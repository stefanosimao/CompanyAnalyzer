import os
import re
import uuid
import logging
from datetime import datetime
from pathlib import Path
from threading import Thread
from typing import Any, Dict, List, Union
import pandas as pd
from google import genai
from google.genai.types import GenerateContentConfig, GoogleSearch, Tool
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from . import utils, config, gemini_client
import os

from . import utils, config

# Configure module-level logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

def _background_worker(
    companies: pd.DataFrame,
    report_id: str,
    report_name: str,
    gemini_api_key: str,
    pe_firms_list: List[str]
) -> None:
    start = datetime.now()
    logger.info('Background worker started for report ID: %s', report_id)
    results = []
    unique_pe = set()
    newly_discovered_pe_firms = set()
    
    company_names = [str(name).strip() for name in companies['Company Name'].dropna() if name]

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_company = {}
        for name in company_names:
            future = executor.submit(gemini_client.analyze_company, name, gemini_api_key, pe_firms_list, newly_discovered_pe_firms)
            future_to_company[future] = name
            time.sleep(0.5)  # Stagger requests to avoid hitting rate limits
        
        for future in as_completed(future_to_company):
            company_name = future_to_company[future]
            try:
                data = future.result()
                results.append(data)
                if data.get('is_pe_owned') and data.get('pe_owner_names'):
                    unique_pe.update(data.get('pe_owner_names', []))
            except Exception as exc:
                logger.error('%r generated an exception: %s', company_name, exc)
                results.append({
                    'company_name': company_name,
                    'error': f'An exception occurred: {exc}'
                })

    if newly_discovered_pe_firms:
        logger.info(f"Discovered {len(newly_discovered_pe_firms)} new PE firms. Updating master list.")
        # Combine the original list with the unique new firms and sort it
        updated_pe_firms = sorted(list(set(pe_firms_list) | newly_discovered_pe_firms))
        utils.save_pe_firms(updated_pe_firms)
    
    pe_firms_insights = {}
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_pe = {executor.submit(gemini_client.research_pe_portfolio, pe_name, gemini_api_key): pe_name for pe_name in unique_pe}
        for future in as_completed(future_to_pe):
            pe_name = future_to_pe[future]
            try:
                pe_firms_insights[pe_name] = future.result()
            except Exception as exc:
                 logger.error('%r generated an exception during PE research: %s', pe_name, exc)
                 pe_firms_insights[pe_name] = {'name': pe_name, 'error': f'An exception occurred: {exc}'}

    verified_results = _cross_reference_results(results, pe_firms_insights)
    end = datetime.now()
    duration_seconds = (end - start).total_seconds()
    report = {
        'report_name': report_name,
        'data': verified_results,
        'pe_firms_insights': pe_firms_insights,
        'analysis_duration_seconds': duration_seconds,
        'analysis_start_time': start.isoformat(),
        'analysis_end_time': end.isoformat()
    }
    path = Path(config.REPORTS_FOLDER) / f"{report_id}.json"
    utils.save_json_file(str(path), report)
    
    history = utils.load_history()
    for entry in history:
        if entry['id'] == report_id:
            entry.update({
                'status': 'Completed',
                'file_path': str(path),
                'completed_at': datetime.now().isoformat(),
                'analysis_duration_seconds': duration_seconds
            })
            break
            
    utils.save_history(history)
    logger.info('Background worker completed for report ID: %s', report_id)

def start_company_analysis(companies_df: pd.DataFrame) -> Dict[str, str]:
    gemini_api_key = os.environ.get('GEMINI_API_KEY')
    if not gemini_api_key:
        logger.error('GEMINI_API_KEY is not configured. Please set it in your .env file.')
        return {'error': 'GEMINI_API_KEY is not configured. Please set it in your .env file.'}

    
    if not gemini_api_key:
        logger.error('Gemini API Key is not configured. Please set it in settings.')
        return {'error': 'Gemini API Key is not configured. Please set it in settings.'}

    report_id = str(uuid.uuid4())
    report_name = f"Analysis Report - {datetime.now():%Y-%m-%d %H:%M:%S}"

    history = utils.load_history()
    history.insert(0, {
        'id': report_id,
        'name': report_name,
        'date': datetime.now().isoformat(),
        'status': 'Pending',
        'num_companies': len(companies_df),
        'file_path': None,
        'completed_at': None,
        'analysis_duration_seconds': None
    })
    utils.save_history(history)

    Thread(
        target=_background_worker,
        args=(companies_df, report_id, report_name, gemini_api_key, utils.load_pe_firms()),
        daemon=True
    ).start()

    logger.info('Analysis started for report ID: %s', report_id)
    return {'message': 'File uploaded and analysis started! You can check the history for status.', 'report_id': report_id, 'report_name': report_name}

def _cross_reference_results(
    company_results: List[Dict[str, Any]],
    pe_insights: Dict[str, Any]
) -> List[Dict[str, Any]]:
        
    logger.info("Starting cross-referencing and verification step...")
    
    # Create a simple lookup map of portfolio companies to their PE owners
    portfolio_to_owner_map = {}
    for pe_name, insights in pe_insights.items():
        if insights.get('portfolio_companies'):
            for company in insights['portfolio_companies']:
                original_name = company.get('name')
                if original_name:
                    normalized_name = _normalize_company_name(original_name)
                    if normalized_name not in portfolio_to_owner_map:
                        portfolio_to_owner_map[normalized_name] = []
                    portfolio_to_owner_map[normalized_name].append(pe_name)

    # Iterate through the original results to find and correct misses
    for company in company_results:
        # We now check any company that isn't already categorized as PE-backed or owned.
        if company.get('ownership_category') not in ['PE-Owned', 'Public (PE-Backed)']:
            original_name = company.get('company_name')
            normalized_name = _normalize_company_name(original_name)
            
            if normalized_name in portfolio_to_owner_map:
                owners = portfolio_to_owner_map[normalized_name]
                logger.warning(
                    f"CORRECTION: Found missed PE relationship for '{original_name}'. "
                    f"Owned by: {', '.join(owners)}."
                )
                
                # --- This is the new, smarter logic ---
                # 1. Update the main flag
                company['is_pe_owned'] = True
                company['flagged_as_pe_account'] = True
                
                # 2. Intelligently set the new category
                if company.get('public_private') == 'Public':
                    company['ownership_category'] = 'Public (PE-Backed)'
                else:
                    company['ownership_category'] = 'PE-Owned'

                # 3. Add the discovered owners, avoiding duplicates
                existing_owners = set(company.get('pe_owner_names', []))
                for owner in owners:
                    existing_owners.add(owner)
                company['pe_owner_names'] = sorted(list(existing_owners))

                # 4. Add a note about the correction
                correction_note = "Ownership corrected by cross-referencing PE portfolio data."
                summary = company.get('ownership_structure', 'N/A')
                if summary and summary != 'N/A':
                    company['ownership_structure'] = f"{summary} NOTE: {correction_note}"
                else:
                    company['ownership_structure'] = correction_note
                    
    logger.info("Cross-referencing finished.")
    return company_results

def _normalize_company_name(name: str) -> str:

    if not isinstance(name, str):
        return ""
        
    name = name.lower()
    
    # List of common suffixes to remove (as whole words)
    suffixes = [
        'inc', 'llc', 'lp', 'ltd', 'gmbh', 'sa', 'ag', 'nv', 'bv',
        'corporation', 'corp', 'company', 'co', 'limited', 'holding', 'holdings'
    ]
    
    # Remove punctuation
    name = re.sub(r'[.,;()]', '', name)
    
    # Remove suffixes
    words = name.split()
    words = [word for word in words if word not in suffixes]
    
    return ' '.join(words).strip()
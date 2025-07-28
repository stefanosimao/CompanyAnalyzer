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
import json

from . import utils, config

# Configure module-level logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

def _configure_genai(api_key: str):
    return genai.Client(api_key=api_key)

def _init_config() -> GenerateContentConfig:
    """Instantiates a configured Gemini model with tools and settings."""
    return GenerateContentConfig(
        tools=[Tool(google_search=GoogleSearch())],
        temperature=0.3
    )

def _extract_text(response: Any) -> str:
    """Concatenate text parts from the first candidate of a Gemini response."""
    candidates = getattr(response, 'candidates', [])
    if not candidates:
        return getattr(response, 'text', '')
    parts = getattr(candidates[0].content, 'parts', [])
    return ''.join(getattr(part, 'text', '') for part in parts)

def analyze_company(
    company_name: str,
    gemini_api_key: str,
    pe_firms_list: List[str],
    newly_discovered_pe_firms: set  
) -> Dict[str, Union[str, bool, List[str], List[Dict[str, str]], None]]:

    logger.info('Initiating analysis for company: %s', company_name)
    public_managers_list = [name.lower() for name in utils.load_public_asset_managers()]
    data = {
        'company_name': company_name,
        'ownership_structure': 'N/A',
        'public_private': 'Unknown',
        'ownership_category': 'Unknown',
        'is_pe_owned': False,
        'pe_owner_names': [],
        'is_itself_pe': False,
        'nation': 'Unknown',
        'flagged_as_pe_account': False,
        'source_snippets': [],
        'error': None
    }

    initial_prompt = f"""
        Analyze the corporate ownership of the company: '{company_name}'.

        Your task is to return a JSON object with the following exact structure and nothing else:
        {{
          "chain_of_thought": "Your reasoning process. First, determine if the company is public or private. Second, identify its major owners. Third, based on the owners, select the most accurate ownership_category. Finally, list any PE firms and the headquarters nation.",
          "public_private": "Public or Private",
          "ownership_category": "One of: PE-Owned, Public (PE-Backed), Public (Institutional), Private (Founder/Family), Private (Other), Unknown",
          "pe_owner_names": ["List of PE firm names, or an empty list"],
          "nation": "Headquarters country name",
          "ownership_summary": "A brief, one-sentence summary of the ownership structure."
        }}
        "**IMPORTANT RULE**: If you cannot find specific information from a reliable source, you MUST state 'Information not found'. Do not infer or guess answers.\n\n"
        ---
        EXAMPLE:
        Company: 'Garrett Motion Inc.'

        JSON Output:
        {{
          "chain_of_thought": "First, I determined that Garrett Motion Inc. is traded on the Nasdaq (GTX), making it a 'Public' company. Second, I identified its largest shareholders, which include institutional investors like Oaktree Capital Management and Centerbridge Partners, which are PE-like firms. Therefore, the best category is 'Public (PE-Backed)'. I will list these firms as the PE owners and find its headquarters nation.",
          "public_private": "Public",
          "ownership_category": "Public (PE-Backed)",
          "pe_owner_names": ["Oaktree Capital Management", "Centerbridge Partners"],
          "nation": "Switzerland",
          "ownership_summary": "A public company whose largest shareholders are major institutional and PE-like investment firms."
        }}
        ---

        Now, perform the analysis for the company: '{company_name}'.
        """

    try:
        client = _configure_genai(gemini_api_key)
        config = _init_config()

        response_text = ""
        ownership_data = None

        # --- Retry Loop ---
        for attempt in range(2):
            prompt = initial_prompt
            
            # If this is a retry attempt, use a special "correction" prompt
            if attempt > 0:
                logger.warning(f"Retrying JSON parsing for {company_name}. Attempt {attempt + 1}.")
                prompt = f"""
                The previous response for the company '{company_name}' was not valid JSON.
                Please correct the following text and return ONLY the valid JSON object.

                Your task is to return a JSON object with the following exact structure and nothing else:
                {{
                  "chain_of_thought": "Your reasoning process...",
                  "public_private": "Public or Private",
                  "ownership_category": "One of: PE-Owned, Public (PE-Backed), Public (Institutional), Private (Founder/Family), Private (Other), Unknown",
                  "pe_owner_names": ["List of PE firm names, or an empty list"],
                  "nation": "Headquarters country name",
                  "ownership_summary": "A brief, one-sentence summary of the ownership structure."
                }}

                ---
                EXAMPLE JSON Output:
                {{
                  "chain_of_thought": "First, I determined that Garrett Motion Inc. is traded on the Nasdaq (GTX)...",
                  "public_private": "Public",
                  "ownership_category": "Public (PE-Backed)",
                  "pe_owner_names": ["Oaktree Capital Management", "Centerbridge Partners"],
                  "nation": "Switzerland",
                  "ownership_summary": "A public company whose largest shareholders are major institutional and PE-like investment firms."
                }}
                ---
                
                PREVIOUS INVALID RESPONSE TO CORRECT:
                {response_text}
                ---

                CORRECTED JSON ONLY:
                """

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=config,
            )
            response_text = _extract_text(response)

            try:
                json_str = response_text.strip().replace('`', '').replace('json', '')
                ownership_data = json.loads(json_str)
                # If parsing succeeds, break out of the loop
                break
            except (json.JSONDecodeError, AttributeError):
                # If parsing fails, the loop will continue to the next attempt
                ownership_data = None
                continue

        # After the loop, check if we were successful
        if ownership_data:
            category = ownership_data.get('ownership_category', 'Unknown')
            pe_owners = ownership_data.get('pe_owner_names', [])

            data.update({
                'public_private': ownership_data.get('public_private', 'Unknown'),
                'ownership_category': category,
                'pe_owner_names': pe_owners,
                'nation': ownership_data.get('nation', 'Unknown'),
                'ownership_structure': ownership_data.get('ownership_summary', 'N/A')
            })

            if category in ['PE-Owned', 'Public (PE-Backed)']:
                data['is_pe_owned'] = True
                data['flagged_as_pe_account'] = True

            if pe_owners:
                for pe_firm in pe_owners:
                    is_already_known = any(pe_firm.lower() == known_firm.lower() for known_firm in pe_firms_list)
                    if not is_already_known:
                        newly_discovered_pe_firms.add(pe_firm)
        else:
            # If ownership_data is still None after all attempts, set the error
            data['error'] = "Failed to parse AI response as JSON after multiple attempts."
            logger.error(f"Could not decode JSON for {company_name} after retries. Final response: {response_text}")

    except Exception as e:
        logger.exception("Error analyzing %s with Gemini", company_name)
        data['error'] = f'An unexpected error occurred during analysis: {e}'

    return data

def research_pe_portfolio(pe_name: str, gemini_api_key: str) -> Dict[str, Any]:

    logger.info('Initiating secondary research for PE firm: %s', pe_name)
    result = {'name': pe_name, 'profile_summary': 'N/A', 'portfolio_companies': [], 'error': None}

    # A detailed prompt asking for a specific JSON structure
    initial_prompt = f"""
    Provide a detailed profile and a list of portfolio companies for the Private Equity firm: '{pe_name}'.

    Your task is to return a JSON object with the following exact structure and nothing else:
    {{
      "profile_summary": "A concise, one-paragraph summary of the PE firm.",
      "portfolio_companies": [
        {{
          "name": "Company Name",
          "headquarters": "Headquarters Country",
          "industry": "Primary Industry"
        }}
      ]
    }}

    ---
    EXAMPLE:
    PE Firm: 'Bain Capital'

    JSON Output:
    {{
      "profile_summary": "Bain Capital is a global private investment firm based in Boston, Massachusetts. It specializes in private equity, venture capital, credit, public equity, impact investing, life sciences, and real estate. The firm has invested in or acquired hundreds of companies.",
      "portfolio_companies": [
        {{ "name": "StarkWare", "headquarters": "Israel", "industry": "Technology" }},
        {{ "name": "Coyol Free Zone", "headquarters": "Costa Rica", "industry": "Industrial" }},
        {{ "name": "EcoCeres, Inc.", "headquarters": "USA", "industry": "Bio-refinery" }}
      ]
    }}
    ---

    Now, perform the research for the PE firm: '{pe_name}'. If no portfolio companies are found, return an empty list.
    """

    try:
        client = _configure_genai(gemini_api_key)
        config = _init_config()
        response_text = ""
        portfolio_data = None

        # Retry loop for JSON parsing
        for attempt in range(2):
            prompt = initial_prompt
            if attempt > 0:
                logger.warning(f"Retrying JSON parsing for PE firm {pe_name}. Attempt {attempt + 1}.")
                prompt = f"The previous response was not valid JSON. Please correct it and return ONLY the valid JSON object for '{pe_name}'.\n\nPREVIOUS INVALID RESPONSE:\n{response_text}\n\nCORRECTED JSON ONLY:"

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=config,
                )
            response_text = _extract_text(response)

            try:
                json_str = response_text.strip().replace('`', '').replace('json', '')
                portfolio_data = json.loads(json_str)
                break
            except (json.JSONDecodeError, AttributeError):
                portfolio_data = None
                continue
        
        if portfolio_data:
            result['profile_summary'] = portfolio_data.get('profile_summary', 'N/A')
            result['portfolio_companies'] = portfolio_data.get('portfolio_companies', [])
        else:
            result['error'] = "Failed to parse AI response for PE portfolio as JSON after multiple attempts."
            logger.error(f"Could not decode PE portfolio JSON for {pe_name} after retries. Final response: {response_text}")

    except Exception as e:
        logger.exception("Error researching %s with Gemini", pe_name)
        result['error'] = 'An unexpected error occurred during PE research.'

    logger.info('Finished PE research for %s. Portfolio companies found: %d', pe_name, len(result['portfolio_companies']))
    return result

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
            # Pass the set to each thread
            future = executor.submit(analyze_company, name, gemini_api_key, pe_firms_list, newly_discovered_pe_firms)
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
        future_to_pe = {executor.submit(research_pe_portfolio, pe_name, gemini_api_key): pe_name for pe_name in unique_pe}
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
    settings = utils.load_settings()
    gemini_api_key = settings.get('gemini_api_key')
    
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
import os
import re
import uuid
import logging
from datetime import datetime
from pathlib import Path
from threading import Thread
from typing import Any, Dict, List, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from google import genai
from google.genai import types

from . import utils, config

# Configure module-level logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

def _configure_genai(api_key: str) -> genai.Client:
    """Set up the Gemini API key."""
    return genai.Client(api_key=api_key)

def _init_config() -> types.GenerateContentConfig:
    """Instantiate a configured Gemini model with tools and settings."""
    grounding_tool = types.Tool(google_search=types.GoogleSearch())
    return types.GenerateContentConfig(
        tools=[grounding_tool],
        temperature=0.2
    )

def _extract_text(response: Any) -> str:
    """Concatenate text parts from the first candidate of a Gemini response."""
    candidates = getattr(response, 'candidates', [])
    if not candidates:
        return getattr(response, 'text', '')
    parts = getattr(candidates[0].content, 'parts', [])
    return ''.join(getattr(part, 'text', '') for part in parts)


def _extract_grounding(response: Any) -> List[Dict[str, str]]:
    """Extract grounding attributions (snippet, url, title) from response."""
    snippets: List[Dict[str, str]] = []
    
    feedback = getattr(response, 'prompt_feedback', None)
    if feedback and hasattr(feedback, 'grounding_attributions') and feedback.grounding_attributions:
        for attr in feedback.grounding_attributions:
            uri = getattr(attr, 'web_uri', None) or getattr(attr, 'uri', None)
            if uri:
                snippets.append({
                    'snippet': getattr(attr, 'snippet', ''),
                    'url': uri,
                    'source_title': getattr(attr, 'title', '')
                })
        return snippets

    if hasattr(response, 'candidates') and response.candidates:
        for cand in response.candidates:
            if hasattr(cand, 'grounding_attributions') and cand.grounding_attributions:
                for attr in cand.grounding_attributions:
                    uri = getattr(attr, 'uri', None) or getattr(attr, 'web_uri', None)
                    if uri:
                        snippets.append({
                            'snippet': getattr(attr, 'content', 'No snippet provided'),
                            'url': uri,
                            'source_title': getattr(attr, 'title', 'Unknown Source')
                        })
    return snippets

def _verify_and_extract_pe_name(
    owners_txt: str,
    company_name: str,
    gemini_api_key: str
) -> Union[str, None]:
    """
    Makes a second, targeted call to Gemini to verify if a text describes a PE firm
    and extract its proper name.
    """
    logger.info(f"Running verification step for potential PE ownership of {company_name}.")
    prompt = (
        "Based on the following text, answer two questions:\n\n"
        f"Text: \"{owners_txt}\"\n\n"
        "1. Is the primary owner mentioned in this text a Private Equity firm? (Answer only with 'Yes' or 'No').\n"
        "2. If yes, what is the exact, full, proper name of that Private Equity firm? (If no, respond with 'N/A').\n\n"
        "Example Response:\n"
        "1. Yes\n"
        "2. SK Capital Partners"
    )

    try:
        client = _configure_genai(gemini_api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = _extract_text(response)

        is_pe_firm_match = re.search(r"1\.\s*Yes", text, re.IGNORECASE)
        if is_pe_firm_match:
            pe_name_match = re.search(r"2\.\s*(.+)", text)
            if pe_name_match:
                pe_name = pe_name_match.group(1).strip()
                if pe_name.lower() != 'n/a':
                    logger.info(f"Verification successful. Extracted PE Firm: {pe_name}")
                    return pe_name
    except Exception as e:
        logger.error(f"Error during PE verification call: {e}")
        
    return None

def _verify_public_private_status(
    owners_txt: str,
    company_name: str,
    gemini_api_key: str
) -> Union[str, None]:
    """
    Makes a targeted call to resolve ambiguity in the public/private status.
    """
    logger.info(f"Running verification for public/private status of {company_name}.")
    prompt = (
        "Based on the following ownership description, is the company Publicly Traded or Privately Held? "
        "Answer only with the single word 'Public' or 'Private'.\n\n"
        f"Ownership Description: \"{owners_txt}\""
    )
    try:
        client = _configure_genai(gemini_api_key)
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        text = _extract_text(response).strip()
        if text in ["Public", "Private"]:
            logger.info(f"Status verification for {company_name} returned: {text}")
            return text
    except Exception as e:
        logger.error(f"Error during status verification call: {e}")

    return None

def _extract_all_pe_firms_from_text(
    owners_txt: str,
    company_name: str,
    gemini_api_key: str
) -> List[str]:
    """
    Uses a targeted Gemini call to act like an analyst and extract all PE firm names
    from a block of text.
    """
    logger.info(f"Running advanced PE extraction for {company_name}.")
    prompt = (
        "You are an expert financial analyst. Read the following text describing the ownership of "
        f"'{company_name}'. Your task is to identify and extract the names of all Private Equity firms, "
        "investment funds, or similar entities mentioned.\n\n"
        f"Ownership Text: \"{owners_txt}\"\n\n"
        "List the exact, full, proper names of all the private equity or investment firms you can identify. "
        "If you find none, respond with a single 'N/A'.\n"
        "Provide the list separated by commas.\n\n"
        "Example Response:\n"
        "Strategic Value Partners, LLC, Ares Management, TowerBrook Capital Partners, Cross Ocean Partners"
    )

    try:
        client = _configure_genai(gemini_api_key)
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        text = _extract_text(response).strip()

        if text.lower() == 'n/a' or not text:
            return []
        
                # Smartly rejoin suffixes like Inc., LLC, etc. that get split by commas.
        raw_names = [name.strip() for name in text.split(',')]
        corrected_names = []
        i = 0
        while i < len(raw_names):
            current_name = raw_names[i]
            # Check if the next part is a common corporate suffix.
            if i + 1 < len(raw_names) and raw_names[i+1].lower().replace('.', '') in ['inc', 'llc', 'lp', 'gmbh', 'sa', 'sas', 'ag']:
                # Join it with the current name
                corrected_names.append(f"{current_name}, {raw_names[i+1]}")
                i += 2 # Skip the next element since we've consumed it
            else:
                corrected_names.append(current_name)
                i += 1

        logger.info(f"Advanced extraction found PE firms: {corrected_names}")
        return corrected_names

    except Exception as e:
        logger.error(f"Error during advanced PE extraction call: {e}")
        return []

def analyze_company(
    company_name: str,
    gemini_api_key: str,
    pe_firms_list: List[str]
) -> Dict[str, Union[str, bool, List[str], List[Dict[str, str]], None]]:
    """
    Analyze a company via Gemini: public/private status, ownership, financials, etc.
    """
    logger.info('Initiating analysis for company: %s', company_name)
    nations_list = utils.load_nations()
    data = {
        'company_name': company_name,
        'ownership_structure': 'N/A',
        'public_private': 'Unknown',
        'is_pe_owned': False,
        'pe_owner_names': [],
        'is_itself_pe': False,
        'nation': 'Unknown',
        'flagged_as_pe_account': False,
        'source_snippets': [],
        'error': None
    }

    try:
        client = _configure_genai(gemini_api_key)
        config = _init_config()

        # --- ADVANCED PROMPT ENGINEERING ---
        # Added a high-quality "few-shot" example and a strict constraint.
        prompt = (
            f"Please find comprehensive information for the company '{company_name}'. "
            "Specifically, identify the following details:\n"
            "1. **Public/Private Ownership:** Is the company publicly traded or privately owned? (Respond concisely as 'Public' or 'Private' or 'Unknown')\n"
            "2. **Ownership Structure:** If private, who are its primary owners? This includes Private Equity firms, Investment Banking owned PEs, Institutional Investors, Pension Funds, Family Funds, Founders, or other major entities. List the specific names of these owners.\n"
            "3. **Self-Identification as PE:** Is '{company_name}' itself a Private Equity firm or an investment company? (Respond concisely as 'Yes' or 'No')\n"
            "4. **Nation (Headquarters):** In which single nation is its primary headquarters located? (ANSWER WITH ONLY THE COUNTRY NAME, e.g., 'USA', 'Switzerland')\n\n"
            "**IMPORTANT RULE**: If you cannot find specific information from a reliable source, you MUST state 'Information not found'. Do not infer or guess answers.\n\n"
            "**CHAIN-OF-THOUGHT INSTRUCTION**: First, provide a brief step-by-step reasoning for your conclusions on Ownership, PE Status, and Nation. After your reasoning, provide the final numbered list answer based on the example format below.\n\n"
            "--- Example Start ---\n"
            "Company: 'Stripe'\n\n"
            "1. **Public/Private Ownership:** Private\n"
            "2. **Ownership Structure:** Founders (Patrick and John Collison), Sequoia Capital, Andreessen Horowitz, and other venture capital firms.\n"
            "3. **Self-Identification as PE:** No\n"
            "4. **Nation (Headquarters):** USA\n"
            "--- Example End ---"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config,
        )

        text = _extract_text(response)
        if not text:
            msg = f"Gemini returned no text content for {company_name}."
            logger.warning(msg)
            data['error'] = msg
            return data

        data['source_snippets'] = _extract_grounding(response)
        text_lower = text.lower()
        
        # --- PARSING LOGIC ---
        if "public/private ownership:** public" in text_lower or "publicly traded" in text_lower:
            data["public_private"] = "Public"
        elif "public/private ownership:** private" in text_lower or "privately owned" in text_lower:
            data["public_private"] = "Private"

        owner_match = re.search(r"ownership structure:\*\*(.*?)(?:\n\d|\n\n|$)", text, re.DOTALL | re.IGNORECASE)
        owners_txt = text
        if owner_match:
            owners_txt = owner_match.group(1).strip()
            data["ownership_structure"] = owners_txt
        else:
            data["ownership_structure"] = "Not found in structured format. Full text used for analysis."
        
        extracted_pe_firms = _extract_all_pe_firms_from_text(owners_txt, company_name, gemini_api_key)
        
        if extracted_pe_firms:
            data["is_pe_owned"] = True
            data["pe_owner_names"] = extracted_pe_firms
            # Now, update the main PE list with any newly discovered firms
            for pe_firm in extracted_pe_firms:
                is_already_known = any(pe_firm.lower() == known_firm.lower() for known_firm in pe_firms_list)
                if not is_already_known:
                    logger.info(f"Discovered and verified new PE firm: {pe_firm}. Adding to list.")
                    pe_firms_list.append(pe_firm)
                    utils.save_pe_firms(pe_firms_list)
        
        if re.search(r"self-identification as pe:\*\* yes", text_lower):
            data['is_itself_pe'] = True

        nation_match = re.search(r"nation \(headquarters\):\*\* (.*)", text, re.IGNORECASE)
        if nation_match:
            data["nation"] = nation_match.group(1).strip()

        if nation_match:
            nation_text = nation_match.group(1).strip()
            found_nation = "Unknown"
            for country in nations_list: # Use the loaded list
                if re.search(rf"\b{re.escape(country)}\b", nation_text, re.IGNORECASE):
                    found_nation = country
                    if country.lower() in ["usa", "united states"]: found_nation = "USA"
                    if country.lower() in ["uk", "united kingdom"]: found_nation = "UK"
                    break 
            data["nation"] = found_nation

        # --- HEURISTIC AND AI-POWERED VALIDATION ---
        # Rule 1: A company cannot be both a PE firm and publicly traded.
        if data['is_itself_pe'] and data['public_private'] == 'Public':
            logger.warning(f"Validation failed for {company_name}: Flagged as PE but also Public. Re-classifying as not a PE firm.")
            data['is_itself_pe'] = False

        # Rule 2: If a company is owned by a PE firm, it must be Private.
        if data["is_pe_owned"] and data["public_private"] != 'Private':
            logger.warning(f"Validation failed for {company_name}: Flagged as PE-owned but not Public. Correcting status to Private.")
            data["public_private"] = "Private"
        
        # Rule 3: AI-powered verification for ambiguous public/private status.
        elif data["public_private"] == 'Public' and not data['is_pe_owned'] and any(keyword in data["ownership_structure"].lower() for keyword in ["foundation", "family", "private investor", "privately owned"]):
             logger.warning(f"Ambiguity detected for {company_name}. Marked Public but ownership text suggests private. Starting verification call.")
             verified_status = _verify_public_private_status(data["ownership_structure"], company_name, gemini_api_key)
             if verified_status:
                data["public_private"] = verified_status

        # Rule 4: If a company is PE-owned, it should be flagged.
        if data["is_pe_owned"]:
            data["flagged_as_pe_account"] = True

    except types.generation_types.BlockedPromptException as e:
        reason = e.response.prompt_feedback.block_reason.name
        logger.error("Gemini API blocked prompt for %s: %s", company_name, reason)
        data['error'] = f"Gemini API blocked prompt: {reason}"
    except Exception:
        logger.exception("Error analyzing %s with Gemini", company_name)
        data['error'] = 'An unexpected error occurred during analysis.'

    logger.info('Finished analysis for %s. Data: %s', company_name, data)
    return data


def research_pe_portfolio(pe_name: str, gemini_api_key: str) -> Dict[str, Union[str, List[Dict[str, str]], None]]:
    """
    Secondary research: profile summary and portfolio companies for a PE firm.
    """
    logger.info('Initiating secondary research for PE firm: %s', pe_name)
    result = {'name': pe_name, 'profile_summary': 'N/A', 'portfolio_companies': [], 'error': None}

    try:
        client = _configure_genai(gemini_api_key)
        config = _init_config()

        prompt = (
            f"Provide a concise profile summary for the Private Equity firm '{pe_name}'.\n"
            f"Then, list its recent and current portfolio companies. For each portfolio company, provide its name, headquarters nation, and primary industry.\n\n"
            f"**CHAIN-OF-THOUGHT INSTRUCTION**: First, briefly explain your search process to identify the portfolio companies. After your reasoning, provide the final answer in the format shown in the example.\n\n"
            f"--- Example Start ---\n"
            f"**Reasoning:** Searched for official portfolio lists on the firm's website and recent acquisition announcements in financial news.\n\n"
            f"**Profile Summary:** Bain Capital is a leading global private investment firm...\n\n"
            f"**Portfolio Companies:**\n"
            f"1. Company X (USA, Software)\n"
            f"2. Company Y (Germany, Automotive)\n"
            f"--- Example End ---\n\n"
            f"If no portfolio companies are found, state 'No recent portfolio companies found'."
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config,
        )
        text = _extract_text(response)
        if not text:
            msg = f"Gemini returned no text content for PE firm {pe_name}."
            logger.warning(msg)
            result['error'] = msg
            return result

        profile_match = re.search(r"profile summary:(.*?)(?=portfolio companies:|$)", text, re.DOTALL | re.IGNORECASE)
        if profile_match:
            result['profile_summary'] = profile_match.group(1).strip()

        portfolio_section_match = re.search(r"portfolio companies:(.*)", text, re.DOTALL | re.IGNORECASE)
        if portfolio_section_match:
            portfolio_text = portfolio_section_match.group(1).strip()
            company_pattern = re.compile(r"^\s*\d+\.\s*(.*?)\s\((.*?),\s*(.*?)\)", re.MULTILINE)
            for match in company_pattern.finditer(portfolio_text):
                result["portfolio_companies"].append({
                    "name": match.group(1).strip(),
                    "headquarters": match.group(2).strip(),
                    "industry": match.group(3).strip()
                })

    except genai.types.BlockedPromptException as e:
        reason = e.response.prompt_feedback.block_reason.name
        logger.error("Gemini API blocked prompt for PE firm %s: %s", pe_name, reason)
        result['error'] = f"Gemini API blocked prompt for PE portfolio: {reason}"
    except Exception:
        logger.exception("Error researching %s with Gemini", pe_name)
        result['error'] = 'An unexpected error occurred during PE research.'

    logger.info('Finished PE research for %s. Portfolio found: %d', pe_name, len(result['portfolio_companies']))
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
    
    company_names = [str(name).strip() for name in companies['Company Name'].dropna() if name]

    with ThreadPoolExecutor(max_workers=500) as executor:
        # Create a future for each company analysis
        future_to_company = {executor.submit(analyze_company, name, gemini_api_key, pe_firms_list): name for name in company_names}
        
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
    
    # The secondary research on PE firms can also be parallelized
    pe_firms_insights = {}
    with ThreadPoolExecutor(max_workers=50) as executor:
        future_to_pe = {executor.submit(research_pe_portfolio, pe_name, gemini_api_key): pe_name for pe_name in unique_pe}
        for future in as_completed(future_to_pe):
            pe_name = future_to_pe[future]
            try:
                pe_firms_insights[pe_name] = future.result()
            except Exception as exc:
                 logger.error('%r generated an exception during PE research: %s', pe_name, exc)
                 pe_firms_insights[pe_name] = {'name': pe_name, 'error': f'An exception occurred: {exc}'}


    end = datetime.now()
    duration_seconds = (end - start).total_seconds()
    report = {
        'report_name': report_name,
        'data': results,
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
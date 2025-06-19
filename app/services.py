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
from google.genai import types

from . import utils, config

# Configure module-level logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

NATIONS = [
    "Switzerland", "Germany", "France", "UK", "United Kingdom", "USA", "United States", "Canada",
    "China", "India", "Japan", "Australia", "Italy", "Spain", "Netherlands",
    "Belgium", "Sweden", "Norway", "Denmark", "Finland", "Austria", "Ireland",
    "Portugal", "Singapore", "South Korea", "Brazil", "Mexico", "South Africa",
    "United Arab Emirates", "Luxembourg", "Cayman Islands", "Jersey", "Guernsey"
]

def _configure_genai(api_key: str) -> genai.Client:
    """Set up the Gemini API key."""
    return genai.Client(api_key=api_key)


def _init_config() -> types.GenerateContentConfig:
    """Instantiate a configured Gemini model with tools."""
    grounding_tool = types.Tool(google_search=types.GoogleSearch())
    return types.GenerateContentConfig(tools=[grounding_tool])


def _extract_text(response: Any) -> str:
    """Concatenate text parts from the first candidate of a Gemini response."""
    candidates = getattr(response, 'candidates', [])
    if not candidates:
        # fallback if someone passed in a bare object with `.text`
        return getattr(response, 'text', '')  
    parts = getattr(candidates[0].content, 'parts', [])
    # join whatever .text exists (defaults to empty string)
    return ''.join(getattr(part, 'text', '') for part in parts)


def _extract_grounding(response: Any) -> List[Dict[str, str]]:
    """Extract grounding attributions (snippet, url, title) from response."""
    snippets: List[Dict[str, str]] = []
    
    # Try prompt_feedback.grounding_attributions first
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

    # Fallback to candidates' grounding_attributions
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


def analyze_company(
    company_name: str,
    gemini_api_key: str,
    pe_firms_list: List[str]
) -> Dict[str, Union[str, bool, List[str], List[Dict[str, str]], None]]:
    """
    Analyze a company via Gemini: public/private status, ownership, financials, etc.
    """
    logger.info('Initiating analysis for company: %s', company_name)
    data = {
        'company_name': company_name,
        'ownership_structure': 'N/A',
        'public_private': 'Unknown',
        'is_pe_owned': False,
        'pe_owner_names': [],
        'is_itself_pe': False,
        'revenue': 'N/A',
        'revenue_year': 'N/A',
        'employees': 'N/A',
        'employees_year': 'N/A',
        'nation': 'Unknown',
        'flagged_as_pe_account': False,
        'source_snippets': [],
        'error': None
    }

    try:
        client = _configure_genai(gemini_api_key)
        config = _init_config()

        # Reverted to more detailed prompt for better structured output
        prompt = (
            f"Please find comprehensive information for the company '{company_name}'. "
            "Specifically, identify the following details:\n"
            "1. **Public/Private Ownership:** Is the company publicly traded or privately owned? (Respond concisely as 'Public' or 'Private' or 'Unknown')\n"
            "2. **Ownership Structure:** If private, who are its primary owners? This includes Private Equity firms, Investment Banking owned PEs, Institutional Investors, Pension Funds, Family Funds, Founders, or other major entities. List the specific names of these owners.\n"
            "3. **Self-Identification as PE:** Is '{company_name}' itself a Private Equity firm or an investment company? (Respond concisely as 'Yes' or 'No')\n"
            "4. **Revenue:** What is its approximate annual revenue? Provide the numerical value, units (e.g., million, billion), and the **year** for which this figure applies (e.g., '$100 million (2023)'). If the year is unknown, just provide the revenue.\n"
            "5. **Employees:** How many employees does it have? Provide the numerical value and the **year** for which this figure applies (e.g., '10,000 employees (2024)'). If the year is unknown, just provide the employee count.\n"
            "6. **Nation (Headquarters):** In which nation is its primary headquarters located?\n\n"
            "Synthesize this information clearly. If information is not found for a point, state 'Not found' or 'N/A'. "
            "Prioritize reliable sources. Do not make up information. Use your internal search tools effectively."
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

        # Public vs Private - Reverted to more robust regex
        if "public/private ownership: public" in text_lower or "publicly traded" in text_lower:
            data["public_private"] = "Public"
        elif "public/private ownership: private" in text_lower or "privately owned" in text_lower:
            data["public_private"] = "Private"
        else: # Fallback to regex
            if re.search(r'\bpublic(?:ly| traded)? (?:company|entity)\b', text_lower):
                data["public_private"] = "Public"
            elif re.search(r'\bprivate(?:ly| owned| held)? (?:company|entity)\b', text_lower):
                data["public_private"] = "Private"

        # Self-PE check - Kept existing robust regex
        if re.search(r"\bis (?:itself )?a private equity firm\b", text_lower):
            data['is_itself_pe'] = True
            data['public_private'] = 'Private'

        # Ownership structure - Reverted regex for better section termination
        owner_match = re.search(r"ownership structure:(.*?)(?:\n\d\.|$)", text, re.DOTALL | re.IGNORECASE)
        if owner_match:
            owners_txt = owner_match.group(1).strip()
            data["ownership_structure"] = owners_txt

            potential_owners = []
            for pe_firm in pe_firms_list:
                # Improved: Use re.search with word boundaries and re.escape
                if re.search(rf"\b{re.escape(pe_firm.lower())}\b", owners_txt.lower()):
                    data["is_pe_owned"] = True
                    data["pe_owner_names"].append(pe_firm)
            
            if re.search(r'\b(?:family|founder|individual|private investor)\b', owners_txt.lower()):
                potential_owners.append("Family/Private Individuals")
            if re.search(r'\b(?:institutional investor|pension fund|sovereign wealth fund)\b', owners_txt.lower()):
                potential_owners.append("Institutional Investors")
            if re.search(r'\b(?:investment banking|venture capital)\b', owners_txt.lower()):
                potential_owners.append("Investment Firms/VC")

            if not data["is_pe_owned"] and potential_owners:
                data["ownership_structure"] = ", ".join(list(set(potential_owners)))
            elif data["is_pe_owned"]:
                # Ensure existing owners are combined with identified PE owners
                existing_owners = [o.strip() for o in data["ownership_structure"].split(',') if o.strip()]
                all_owners = list(set(data["pe_owner_names"] + existing_owners))
                data["ownership_structure"] = ", ".join(all_owners)
            
            if data["is_pe_owned"]:
                data["flagged_as_pe_account"] = True


        # Revenue
        rev = re.search(
            r"(?:revenue|annual revenue|turnover):\s*(\$|€|£)?\s*([\d\.,]+)\s*(?:million|billion|k|M|B|trillion)?\s*(?:year\s*)?\(?(\d{4})?\)?",
            text_lower
        )
        if rev:
            currency = rev.group(1) if rev.group(1) else ""
            amount = rev.group(2).replace(",", "")
            unit = rev.group(3) if rev.group(3) else ""
            year = rev.group(4) if rev.group(4) else "N/A"
            
            if unit.lower() == 'k': unit = 'thousand'
            elif unit.lower() == 'm': unit = 'million'
            elif unit.lower() == 'b': unit = 'billion'
            
            data["revenue"] = f"{currency}{amount} {unit}".strip()
            data["revenue_year"] = year

        # Employees
        emp = re.search(
            r"(?:employees|staff|workforce|headcount):\s*([\d\.,]+)\s*(?:employees)?\s*(?:year\s*)?\(?(\d{4})?\)?",
            text_lower
        )
        if emp:
            data["employees"] = emp.group(1).replace(",", "")
            data["employees_year"] = emp.group(2) if emp.group(2) else "N/A"

        # Nation - Reverted to more robust extraction logic
        nation_match = re.search(r"nation \(headquarters\):\s*([A-Za-z\s-]+(?:, [A-Za-z\s-]+)?)", text, re.IGNORECASE)
        if nation_match:
            data["nation"] = nation_match.group(1).strip()
        else: # Fallback to general keyword matching with word boundaries
            for nation in NATIONS:
                # Improved: Use re.search with word boundaries and re.escape
                if re.search(rf'\b{re.escape(nation.lower())}\b', text_lower):
                    data["nation"] = nation
                    break

    except genai.types.BlockedPromptException as e:
        reason = e.response.prompt_feedback.block_reason.name
        logger.error("Gemini API blocked prompt for %s: %s", company_name, reason)
        data['error'] = f"Gemini API blocked prompt: {reason}"
    except Exception:
        logger.exception("Error analyzing %s with Gemini", company_name)
        data['error'] = 'An unexpected error occurred during analysis.'

    logger.info('Finished analysis for %s. Data: %s', company_name, data)
    return data


def research_pe_portfolio(pe_name: str, gemini_api_key: str) -> Dict[str, Union[str, List[Dict[str, str]], None]]: # Corrected type hint
    """
    Secondary research: profile summary and portfolio companies for a PE firm.
    """
    logger.info('Initiating secondary research for PE firm: %s', pe_name)
    result = {'name': pe_name, 'profile_summary': 'N/A', 'portfolio_companies': [], 'error': None}

    try:
        client = _configure_genai(gemini_api_key)
        config = _init_config()

        # Reverted to more detailed prompt for better structured output
        prompt = (
            f"Provide a concise profile summary for the Private Equity firm '{pe_name}'.\n"
            f"Then, list its recent and current portfolio companies. For each portfolio company, provide its name, headquarters nation, and primary industry.\n"
            "Format the portfolio companies as a numbered list with each item showing 'Name (Headquarters, Industry)'.\n"
            "Example:\n"
            "Profile Summary: Bain Capital is a leading global private investment firm...\n"
            "Portfolio Companies:\n"
            "1. Company X (USA, Software)\n"
            "2. Company Y (Germany, Automotive)\n"
            "If no portfolio companies are found, state 'No recent portfolio companies found'."
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

        # Extract summary
        profile_match = re.search(r"profile summary:(.*?)(?:portfolio companies:|error:|no recent portfolio companies found|\n\d\.|$)", text, re.DOTALL | re.IGNORECASE)
        if profile_match:
            result['profile_summary'] = profile_match.group(1).strip()
            if result["profile_summary"].lower().startswith("profile summary:"):
                result["profile_summary"] = result["profile_summary"][len("profile summary:"):].strip()

        # Extract portfolio
        portfolio_section_match = re.search(r"portfolio companies:(.*?)(?:\n\d\.|$)", text, re.DOTALL | re.IGNORECASE)
        if portfolio_section_match:
            portfolio_text = portfolio_section_match.group(1).strip()
            company_pattern = re.compile(r"^\s*\d+\.\s*(.+?)\s*\(([^,]+?),\s*(.+?)\)", re.MULTILINE | re.IGNORECASE)
            
            for line in portfolio_text.splitlines():
                line = line.strip()
                if line and not line.lower().startswith("no recent portfolio companies found"):
                    match = company_pattern.match(line)
                    if match:
                        name, headquarters, industry = match.groups()
                        result["portfolio_companies"].append({
                            "name": name.strip(),
                            "headquarters": headquarters.strip(),
                            "industry": industry.strip()
                        })
        
        if not result["portfolio_companies"] and "no recent portfolio companies found" in text.lower():
            result["portfolio_companies"] = [] # Ensure it's an empty list if not found explicitly

    except genai.types.BlockedPromptException as e:
        reason = e.response.prompt_feedback.block_reason.name
        logger.error("Gemini API blocked prompt for PE firm %s: %s", pe_name, reason)
        result['error'] = f"Gemini API blocked prompt for PE portfolio: {reason}"
    except Exception:
        logger.exception("Error researching %s with Gemini", pe_name)
        result['error'] = 'An unexpected error occurred during PE research.'

    logger.info('Finished PE research for %s. Portfolio found: %s', pe_name, len(result['portfolio_companies']) if isinstance(result['portfolio_companies'], list) else 'N/A')
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

    for idx, row in companies.iterrows():
        name = row.get('Company Name')
        if not name or pd.isna(name):
            logger.warning("Skipping empty company name at index %s.", idx)
            continue
        data = analyze_company(str(name).strip(), gemini_api_key, pe_firms_list)
        results.append(data)
        if data.get('is_pe_owned') and data.get('pe_owner_names'):
            unique_pe.update(data.get('pe_owner_names', []))

    pe_firms_insights = {pe: research_pe_portfolio(pe, gemini_api_key) for pe in unique_pe}

    end = datetime.now()
    duration_seconds = (end - start).total_seconds()
    report = {
        'report_name': report_name,
        'data': results,
        'pe_firms_insights': pe_firms_insights, # Corrected: 'pe_insights' changed back to 'pe_firms_insights'
        'analysis_duration_seconds': duration_seconds,
        'analysis_start_time': start.isoformat(),
        'analysis_end_time': end.isoformat()
    }
    path = Path(config.REPORTS_FOLDER) / f"{report_id}.json"
    utils.save_json_file(str(path), report) # Corrected: Convert Path object to string
    
    history = utils.load_history()
    # Find and update the existing history entry, or add a new one if not found (shouldn't happen normally)
    updated = False
    for entry in history:
        if entry['id'] == report_id:
            entry.update({
                'status': 'Completed',
                'file_path': str(path),
                'completed_at': datetime.now().isoformat(),
                'analysis_duration_seconds': duration_seconds
            })
            updated = True
            break
    if not updated:
        logger.warning("Report ID %s not found in history after completion. Adding as new entry.", report_id)
        history.insert(0, {
            'id': report_id,
            'name': report_name,
            'date': start.isoformat(),
            'status': 'Completed',
            'num_companies': len(companies), # Use original DataFrame length for consistency
            'file_path': str(path),
            'completed_at': datetime.now().isoformat(),
            'analysis_duration_seconds': duration_seconds
        })

    utils.save_history(history)
    logger.info('Background worker completed for report ID: %s', report_id)


def start_company_analysis(companies_df: pd.DataFrame) -> Dict[str, str]:
    settings = utils.load_settings()
    gemini_api_key = settings.get('gemini_api_key')
    
    if not gemini_api_key:
        logger.error('Gemini API Key is not configured. Please set it in settings.')
        return {'error': 'Gemini API Key is not configured. Please set it in settings.'}

    report_id = str(uuid.uuid4())
    report_name = f"Analysis Report - {datetime.now():%Y-%m-%d %H:%M:%S}" # More descriptive name

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
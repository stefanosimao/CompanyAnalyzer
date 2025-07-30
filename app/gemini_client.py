import logging
import json
from typing import Any, Dict, List, Union
from google import genai
from google.genai.types import GenerateContentConfig, GoogleSearch, Tool
import re

from . import utils, config

logger = logging.getLogger(__name__)

def _configure_genai(api_key: str):
    return genai.Client(api_key=api_key)

def _init_config() -> GenerateContentConfig:
    return GenerateContentConfig(
        tools=[Tool(google_search=GoogleSearch())],
        temperature=0.3
    )

def _extract_text(response: Any) -> str:
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
) -> Dict[str, Any]:
    
    logger.info('Initiating analysis for company: %s', company_name)
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
        'error': None,
        'needs_review': False,
        'review_reason': None 
    }

    initial_prompt = config.ANALYZE_COMPANY_PROMPT.format(company_name=company_name)

    try:
        client = _configure_genai(gemini_api_key)
        llm_config = _init_config()

        response_text = ""
        ownership_data = None

        # --- Retry Loop ---
        for attempt in range(2):
            prompt = initial_prompt
            
            # If this is a retry attempt, use a special "correction" prompt
            if attempt > 0:
                logger.warning(f"Retrying JSON parsing for {company_name}. Attempt {attempt + 1}.")
                prompt = config.COMPANY_RETRY_PROMPT.format(company_name=company_name, response_text=response_text)

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=llm_config,
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
            uncertainties = ownership_data.get('uncertainties', [])
            summary_text = ownership_data.get('ownership_summary', 'N/A')
            cleaned_summary = re.sub(r'\s*\[[\d,\s]+\]\s*$', '', summary_text).strip()


            data.update({
                'public_private': ownership_data.get('public_private', 'Unknown'),
                'ownership_category': category,
                'pe_owner_names': pe_owners,
                'nation': ownership_data.get('nation', 'Unknown'),
                'ownership_structure': cleaned_summary
            })

            if category in ['PE-Owned', 'Public (PE-Backed)']:
                data['is_pe_owned'] = True
                data['flagged_as_pe_account'] = True

            # 1. Check for AI-reported uncertainties
            if uncertainties:
                data['needs_review'] = True
                data['review_reason'] = f"AI was uncertain: {'; '.join(uncertainties)}"

            # 2. Perform backend sanity check (Rule-Based)
            if pe_owners and category not in ['PE-Owned', 'Public (PE-Backed)']:
                data['needs_review'] = True
                reason = "Inconsistency: PE owner(s) were identified, but the category is not PE-related."
                # Append to existing reason if there is one
                if data['review_reason']:
                    data['review_reason'] += f" | {reason}"
                else:
                    data['review_reason'] = reason

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

    initial_prompt = config.RESEARCH_PE_PORTFOLIO_PROMPT.format(pe_name=pe_name)
    # A detailed prompt asking for a specific JSON structure
    try:
        client = _configure_genai(gemini_api_key)
        llm_config = _init_config()
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
                config=llm_config,
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
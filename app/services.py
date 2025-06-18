import logging
import re
import uuid
import pandas as pd
from datetime import datetime, timedelta
import threading
import json 
import time
import google.generativeai as genai
from . import utils
from . import config

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def analyze_company(company_name: str, gemini_api_key: str, pe_firms_list: list) -> dict:
    """
    Analyzes a single company by querying the Gemini API with search grounding
    to extract ownership, public/private status, PE ownership, revenue,
    employee count, nation, and the year of revenue/employee data.

    Args:
        company_name: The name of the company to analyze.
        gemini_api_key: The API key for accessing the Gemini API.
        pe_firms_list: A list of known private equity firm names for identification.

    Returns:
        A dictionary containing the extracted company data.
    """
    logging.info(f"Initiating analysis for company: {company_name}")
    company_data = {
        "company_name": company_name,
        "ownership_structure": "N/A",
        "public_private": "Unknown",
        "is_pe_owned": False,
        "pe_owner_names": [],
        "is_itself_pe": False,
        "revenue": "N/A",
        "revenue_year": "N/A",
        "employees": "N/A",
        "employees_year": "N/A",
        "nation": "Unknown",
        "flagged_as_pe_account": False,
        "source_snippets": [],
        "error": None
    }

    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-2.5-flash') 

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

        response = model.generate_content(
            prompt,
            tools=[genai.tool_code.GoogleSearch()],
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        )

        gemini_text_response = ""
        if response and hasattr(response, "candidates") and response.candidates:
            content_parts = getattr(response.candidates[0].content, "parts", [])
            gemini_text_response = "".join(
                part.text for part in content_parts if hasattr(part, "text") and part.text
            )
        
        if not gemini_text_response:
             logging.warning(f"No text content in Gemini response for {company_name}. Full response: {response}")
             company_data["error"] = "Gemini returned no text content."
             return company_data

        logging.debug(f"Gemini raw response for {company_name}:\n{gemini_text_response}")

        if response.prompt_feedback and response.prompt_feedback.grounding_attributions:
            for attribution in response.prompt_feedback.grounding_attributions:
                uri = attribution.web_uri or getattr(attribution, 'uri', None)
                if uri:
                    company_data["source_snippets"].append({
                        "snippet": attribution.snippet,
                        "url": uri,
                        "source_title": attribution.title
                    })
        elif hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'grounding_attributions') and candidate.grounding_attributions:
                    for attribution in candidate.grounding_attributions:
                        uri = getattr(attribution, 'uri', None) or getattr(attribution, 'web_uri', None)
                        if uri:
                            company_data["source_snippets"].append({
                                "snippet": getattr(attribution, 'content', 'No snippet provided'),
                                "url": uri,
                                "source_title": getattr(attribution, 'title', 'Unknown Source')
                            })

        response_lower = gemini_text_response.lower()

        if "public/private ownership: public" in response_lower or "publicly traded" in response_lower:
            company_data["public_private"] = "Public"
        elif "public/private ownership: private" in response_lower or "privately owned" in response_lower:
            company_data["public_private"] = "Private"
        else:
            if re.search(r'\bpublic(?:ly| traded)? (?:company|entity)\b', response_lower):
                company_data["public_private"] = "Public"
            elif re.search(r'\bprivate(?:ly| owned| held)? (?:company|entity)\b', response_lower):
                company_data["public_private"] = "Private"

        if "self-identification as pe: yes" in response_lower or re.search(r'\b(?:is|is itself) a private equity firm\b', response_lower):
            company_data["is_itself_pe"] = True
            company_data["public_private"] = "Private"

        owner_match = re.search(r"ownership structure:(.*?)(?:\n\d\.|$)", gemini_text_response, re.DOTALL | re.IGNORECASE)
        if owner_match:
            owner_text = owner_match.group(1).strip()
            company_data["ownership_structure"] = owner_text

            potential_owners = []
            for pe_firm in pe_firms_list:
                if re.search(rf"\b{re.escape(pe_firm.lower())}\b", owner_text.lower()):
                    company_data["is_pe_owned"] = True
                    company_data["pe_owner_names"].append(pe_firm)
            
            if re.search(r'\b(?:family|founder|individual|private investor)\b', owner_text.lower()):
                potential_owners.append("Family/Private Individuals")
            if re.search(r'\b(?:institutional investor|pension fund|sovereign wealth fund)\b', owner_text.lower()):
                potential_owners.append("Institutional Investors")
            if re.search(r'\b(?:investment banking|venture capital)\b', owner_text.lower()):
                potential_owners.append("Investment Firms/VC")

            if not company_data["is_pe_owned"] and potential_owners:
                company_data["ownership_structure"] = ", ".join(list(set(potential_owners)))
            elif company_data["is_pe_owned"]:
                existing_owners = [o.strip() for o in company_data["ownership_structure"].split(',') if o.strip()]
                all_owners = list(set(company_data["pe_owner_names"] + existing_owners))
                company_data["ownership_structure"] = ", ".join(all_owners)
            
            if company_data["is_pe_owned"]:
                company_data["flagged_as_pe_account"] = True

        revenue_match = re.search(
            r"(?:revenue|annual revenue|turnover):\s*(\$|€|£)?\s*([\d\.,]+)\s*(?:million|billion|k|M|B|trillion)?\s*(?:year\s*)?\(?(\d{4})?\)?",
            gemini_text_response, re.IGNORECASE
        )
        if revenue_match:
            currency = revenue_match.group(1) if revenue_match.group(1) else ""
            amount = revenue_match.group(2).replace(",", "")
            unit = revenue_match.group(3) if revenue_match.group(3) else ""
            year = revenue_match.group(4) if revenue_match.group(4) else "N/A"
            
            if unit.lower() == 'k': unit = 'thousand'
            elif unit.lower() == 'm': unit = 'million'
            elif unit.lower() == 'b': unit = 'billion'
            
            company_data["revenue"] = f"{currency}{amount} {unit}".strip()
            company_data["revenue_year"] = year

        employees_match = re.search(
            r"(?:employees|staff|workforce|headcount):\s*([\d\.,]+)\s*(?:employees)?\s*(?:year\s*)?\(?(\d{4})?\)?",
            gemini_text_response, re.IGNORECASE
        )
        if employees_match:
            company_data["employees"] = employees_match.group(1).replace(",", "")
            company_data["employees_year"] = employees_match.group(2) if employees_match.group(2) else "N/A"

        nation_match = re.search(r"nation \(headquarters\):\s*([A-Za-z\s-]+(?:, [A-Za-z\s-]+)?)", gemini_text_response, re.IGNORECASE)
        if nation_match:
            company_data["nation"] = nation_match.group(1).strip()
        else:
            nations_list = [
                "Switzerland", "Germany", "France", "UK", "United Kingdom", "USA", "United States", "Canada",
                "China", "India", "Japan", "Australia", "Italy", "Spain", "Netherlands", "Belgium",
                "Sweden", "Norway", "Denmark", "Finland", "Austria", "Ireland", "Portugal",
                "Singapore", "South Korea", "Brazil", "Mexico", "South Africa", "UAE", "United Arab Emirates",
                "Luxembourg", "Cayman Islands", "Jersey", "Guernsey"
            ]
            for nation in nations_list:
                if re.search(rf'\b{re.escape(nation)}\b', response_lower):
                    company_data["nation"] = nation
                    break

    except genai.types.BlockedPromptException as e:
        logging.error(f"Gemini API blocked prompt for {company_name}: {e.response.prompt_feedback.block_reason.name}")
        company_data["error"] = f"Gemini API blocked prompt: {e.response.prompt_feedback.block_reason.name}"
    except Exception as e:
        logging.error(f"Error analyzing {company_name} with Gemini: {e}", exc_info=True)
        company_data["error"] = str(e)

    logging.info(f"Finished analysis for {company_name}. Data: {company_data}")
    return company_data

def research_pe_portfolio(pe_firm_name: str, gemini_api_key: str) -> dict:
    """
    Performs secondary research on a given Private Equity firm to find its profile
    and current portfolio companies, their headquarters, and industries.

    Args:
        pe_firm_name: The name of the Private Equity firm.
        gemini_api_key: The API key for accessing the Gemini API.

    Returns:
        A dictionary containing the PE firm's profile and a list of its portfolio companies.
        Example structure:
        {
            "name": "Bain Capital",
            "profile_summary": "...",
            "portfolio_companies": [
                {"name": "Company A", "headquarters": "USA", "industry": "Tech"},
                {"name": "Company B", "headquarters": "Germany", "industry": "Healthcare"}
            ],
            "error": None
        }
    """
    logging.info(f"Initiating secondary research for PE firm: {pe_firm_name}")
    pe_data = {
        "name": pe_firm_name,
        "profile_summary": "N/A",
        "portfolio_companies": [],
        "error": None
    }

    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')

        # Prompt for PE firm profile and portfolio
        prompt = (
            f"Provide a concise profile summary for the Private Equity firm '{pe_firm_name}'.\n"
            f"Then, list its recent and current portfolio companies. For each portfolio company, provide its name, headquarters nation, and primary industry.\n"
            "Format the portfolio companies as a numbered list with each item showing 'Name (Headquarters, Industry)'.\n"
            "Example:\n"
            "Profile Summary: Bain Capital is a leading global private investment firm...\n"
            "Portfolio Companies:\n"
            "1. Company X (USA, Software)\n"
            "2. Company Y (Germany, Automotive)\n"
            "If no portfolio companies are found, state 'No recent portfolio companies found'."
        )

        response = model.generate_content(
            prompt,
            tools=[genai.tool_code.GoogleSearch()],
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        )
        
        gemini_text_response = ""
        if response and hasattr(response, "candidates") and response.candidates:
            content_parts = getattr(response.candidates[0].content, "parts", [])
            gemini_text_response = "".join(
                part.text for part in content_parts if hasattr(part, "text") and part.text
            )

        if not gemini_text_response:
             logging.warning(f"No text content in Gemini response for PE firm {pe_firm_name}. Full response: {response}")
             pe_data["error"] = "Gemini returned no text content for PE portfolio."
             return pe_data

        logging.debug(f"Gemini raw response for PE firm {pe_firm_name}:\n{gemini_text_response}")

        # Extract profile summary
        profile_match = re.search(r"profile summary:(.*?)(?:portfolio companies:|error:|no recent portfolio companies found|\n\d\.|$)", gemini_text_response, re.DOTALL | re.IGNORECASE)
        if profile_match:
            pe_data["profile_summary"] = profile_match.group(1).strip()
            # Clean up potential leading/trailing prompts
            if pe_data["profile_summary"].lower().startswith("profile summary:"):
                pe_data["profile_summary"] = pe_data["profile_summary"][len("profile summary:"):].strip()

        # Extract portfolio companies
        portfolio_section_match = re.search(r"portfolio companies:(.*?)(?:\n\d\.|$)", gemini_text_response, re.DOTALL | re.IGNORECASE)
        if portfolio_section_match:
            portfolio_text = portfolio_section_match.group(1).strip()
            # Pattern for "1. Company X (USA, Software)"
            company_pattern = re.compile(r"^\s*\d+\.\s*(.+?)\s*\(([^,]+?),\s*(.+?)\)", re.MULTILINE | re.IGNORECASE)
            
            for line in portfolio_text.splitlines():
                line = line.strip()
                if line and not line.lower().startswith("no recent portfolio companies found"):
                    match = company_pattern.match(line)
                    if match:
                        name, headquarters, industry = match.groups()
                        pe_data["portfolio_companies"].append({
                            "name": name.strip(),
                            "headquarters": headquarters.strip(),
                            "industry": industry.strip()
                        })
        
        if not pe_data["portfolio_companies"] and "no recent portfolio companies found" in gemini_text_response.lower():
            pe_data["portfolio_companies"] = "No recent portfolio companies found." # Indicate explicitly

    except genai.types.BlockedPromptException as e:
        logging.error(f"Gemini API blocked prompt for PE firm {pe_firm_name}: {e.response.prompt_feedback.block_reason.name}")
        pe_data["error"] = f"Gemini API blocked prompt for PE portfolio: {e.response.prompt_feedback.block_reason.name}"
    except Exception as e:
        logging.error(f"Error researching PE firm {pe_firm_name} portfolio with Gemini: {e}", exc_info=True)
        pe_data["error"] = str(e)

    logging.info(f"Finished secondary research for PE firm: {pe_firm_name}. Portfolio found: {len(pe_data['portfolio_companies'])}")
    return pe_data


def process_companies_in_background(companies_df: pd.DataFrame, report_id: str, report_name: str, gemini_api_key: str, pe_firms_list: list) -> None:
    """
    Background task to process companies from a DataFrame, save the final report,
    and then perform secondary research on identified PE firms.
    This function is designed to be run in a separate thread.
    It also calculates and records the total analysis duration.

    Args:
        companies_df: Pandas DataFrame containing company names.
        report_id: Unique identifier for the report.
        report_name: Human-readable name for the report.
        gemini_api_key: API key for Gemini.
        pe_firms_list: List of known PE firms.
    """
    start_time = datetime.now()
    logging.info(f"Background analysis for report ID {report_id} started at {start_time}.")

    primary_results = []
    unique_pe_owners_found = set() 
    total_companies = len(companies_df)
    
    for i, company_name in enumerate(companies_df['Company Name'].values):
        if pd.isna(company_name) or str(company_name).strip() == "":
            logging.warning(f"Skipping empty company name at index {i}.")
            continue
        company_name_str = str(company_name).strip()

        logging.info(f"Processing {i+1}/{total_companies}: {company_name_str}")
        
        data = analyze_company(company_name_str, gemini_api_key, pe_firms_list)
        primary_results.append(data)

        if data.get("is_pe_owned") and data.get("pe_owner_names"):
            for pe_owner in data["pe_owner_names"]:
                unique_pe_owners_found.add(pe_owner)
    
    pe_firms_insights = {}
    if unique_pe_owners_found:
        logging.info(f"Starting secondary research for {len(unique_pe_owners_found)} unique PE firms.")
        for pe_firm in unique_pe_owners_found:
            pe_firms_insights[pe_firm] = research_pe_portfolio(pe_firm, gemini_api_key)
            time.sleep(0.5)
    else:
        logging.info("No Private Equity firms identified in the primary analysis for secondary research.")

    end_time = datetime.now()
    duration = end_time - start_time
    duration_seconds = duration.total_seconds()
    logging.info(f"Background analysis for report ID {report_id} completed at {end_time}. Duration: {duration}.")

    # Define the path where the completed report will be saved
    report_data = {
        "report_name": report_name,
        "data": primary_results, # Renamed for clarity
        "pe_firms_insights": pe_firms_insights, # NEW: Add PE insights to report
        "analysis_duration_seconds": duration_seconds,
        "analysis_start_time": start_time.isoformat(),
        "analysis_end_time": end_time.isoformat()
    }
    report_path = os.path.join(config.REPORTS_FOLDER, f'{report_id}.json')
    utils.save_json_file(report_path, report_data)
    
    # Update the analysis history with the completion status and duration
    history = utils.load_history()
    updated = False
    for entry in history:
        if entry['id'] == report_id:
            entry["status"] = "Completed"
            entry["file_path"] = report_path
            entry["completed_at"] = datetime.now().isoformat()
            entry["analysis_duration_seconds"] = duration_seconds
            updated = True
            break
    if not updated:
        logging.warning(f"Report ID {report_id} not found in history after completion. Adding new entry.")
        history_entry = {
            "id": report_id,
            "name": report_name,
            "date": start_time.isoformat(),
            "status": "Completed",
            "num_companies": total_companies,
            "file_path": report_path,
            "completed_at": datetime.now().isoformat(),
            "analysis_duration_seconds": duration_seconds
        }
        history.insert(0, history_entry)

    utils.save_history(history)
    logging.info(f"Report '{report_name}' (ID: {report_id}) analysis completed and saved.")

def start_company_analysis(companies_df: pd.DataFrame) -> dict:
    """
    Initiates the company analysis process in a background thread.
    This function is called by the Flask route handler.

    Args:
        companies_df: Pandas DataFrame containing company names from the uploaded Excel.

    Returns:
        A dictionary with status message and report ID/name if successful,
        or an error message.
    """
    settings = utils.load_settings()
    gemini_api_key = settings.get('gemini_api_key')
    pe_firms_list = utils.load_pe_firms()

    if not gemini_api_key:
        logging.error("Gemini API Key is not configured.")
        return {"error": "Gemini API Key is not configured. Please set it in settings."}

    report_id = str(uuid.uuid4())
    report_name = f"Analysis Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    history = utils.load_history()
    history_entry = {
        "id": report_id,
        "name": report_name,
        "date": datetime.now().isoformat(),
        "status": "Pending",
        "num_companies": len(companies_df),
        "file_path": None,
        "completed_at": None,
        "analysis_duration_seconds": None
    }
    history.insert(0, history_entry)
    utils.save_history(history)
    
    thread = threading.Thread(
        target=process_companies_in_background,
        args=(companies_df, report_id, report_name, gemini_api_key, pe_firms_list)
    )
    thread.start()
    logging.info(f"Background analysis thread started for report ID: {report_id}")

    return {
        "message": "File uploaded and analysis started! You can check the history for status.",
        "report_id": report_id,
        "report_name": report_name
    }

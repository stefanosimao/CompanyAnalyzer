import logging
import re
import uuid
import pandas as pd
from datetime import datetime
import threading
import google.generativeai as genai
from . import utils
from . import config
import os

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def analyze_company(company_name: str, gemini_api_key: str, pe_firms_list: list) -> dict:
    """
    Analyzes a single company by querying the Gemini API with search grounding
    to extract ownership, public/private status, PE ownership, revenue,
    employee count, and nation.

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
        "ownership_structure": "N/A", # e.g., "Family-owned", "Owned by John Doe"
        "public_private": "Unknown",  # "Public", "Private", "Unknown"
        "is_pe_owned": False,         # True if identified as owned by a PE firm
        "pe_owner_names": [],         # List of PE firms identified as owners
        "is_itself_pe": False,        # True if the company itself is a PE firm
        "revenue": "N/A",             # Estimated annual revenue
        "revenue_year": "N/A",        
        "employees": "N/A",           # Estimated number of employees
        "employees_year": "N/A",
        "nation": "Unknown",          # Country of headquarters
        "flagged_as_pe_account": False, # Flag if more than 50% ownership by PE (best effort)
        "source_snippets": [],        # Raw snippets and URLs from Gemini's grounding
        "error": None                 # Any error encountered during this company's analysis
    }

    try:
        # Configure Gemini API with the provided key
        genai.configure(api_key=gemini_api_key)
        
        # Initialize the GenerativeModel
        model = genai.GenerativeModel('gemini-2.5-flash') 

        # Craft a precise prompt for Gemini. This prompt instructs the model on what information to find and how to present it.
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

        # Generate content, explicitly enabling Gemini to use Google Search as a tool. The safety settings are added to potentially reduce content blocking for sensitive queries.
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

        # Extract the text response from Gemini
        gemini_text_response = ""
        if response and hasattr(response, "candidates") and response.candidates:
            # Access content parts from the first candidate
            content_parts = getattr(response.candidates[0].content, "parts", [])
            gemini_text_response = "".join(
                part.text for part in content_parts if hasattr(part, "text") and part.text
            )
        
        if not gemini_text_response:
             logging.warning(f"No text content in Gemini response for {company_name}. Full response: {response}")
             company_data["error"] = "Gemini returned no text content."
             return company_data

        logging.debug(f"Gemini raw response for {company_name}:\n{gemini_text_response}")


        # Collect source snippets provided by Gemini's grounding
        if response.prompt_feedback and response.prompt_feedback.grounding_attributions:
            for attribution in response.prompt_feedback.grounding_attributions:
                # Prioritize web_uri, but also check for other URI attributes if structure changes
                uri = attribution.web_uri or getattr(attribution, 'uri', None)
                if uri:
                    company_data["source_snippets"].append({
                        "snippet": attribution.snippet,
                        "url": uri,
                        "source_title": attribution.title
                    })
        elif hasattr(response, 'candidates') and response.candidates:
            # Fallback for newer API response structures or different attribution locations
            for candidate in response.candidates:
                if hasattr(candidate, 'grounding_attributions') and candidate.grounding_attributions:
                    for attribution in candidate.grounding_attributions:
                        uri = getattr(attribution, 'uri', None) or getattr(attribution, 'web_uri', None)
                        if uri:
                            company_data["source_snippets"].append({
                                "snippet": getattr(attribution, 'content', 'No snippet provided'), # Sometimes 'content'
                                "url": uri,
                                "source_title": getattr(attribution, 'title', 'Unknown Source')
                            })


        # --- Information Extraction from Gemini's Text Response (Enhanced Parsing) ---
        # Using regex and keyword matching on Gemini's summarized text.
        response_lower = gemini_text_response.lower()

        # 1. Public vs Private Ownership
        # Look for explicit keywords from Gemini's likely response format
        if "public/private ownership: public" in response_lower or "publicly traded" in response_lower:
            company_data["public_private"] = "Public"
        elif "public/private ownership: private" in response_lower or "privately owned" in response_lower:
            company_data["public_private"] = "Private"
        else: # Attempt a broader check if the explicit format isn't found
            if re.search(r'\bpublic(?:ly| traded)? (?:company|entity)\b', response_lower):
                company_data["public_private"] = "Public"
            elif re.search(r'\bprivate(?:ly| owned| held)? (?:company|entity)\b', response_lower):
                company_data["public_private"] = "Private"

        # 2. Self-Identification as PE
        if "self-identification as pe: yes" in response_lower or re.search(r'\b(?:is|is itself) a private equity firm\b', response_lower):
            company_data["is_itself_pe"] = True
            company_data["public_private"] = "Private"

        # 3. Private Equity Ownership & General Ownership Structure
        # Extract potential owners, then cross-reference with known PE firms
        owner_match = re.search(r"ownership structure:(.*?)(?:\n\d\.|$)", gemini_text_response, re.DOTALL | re.IGNORECASE)
        if owner_match:
            owner_text = owner_match.group(1).strip()
            company_data["ownership_structure"] = owner_text # Store raw ownership text first

            potential_owners = []
            # Look for specific names of known PE firms
            for pe_firm in pe_firms_list:
                # Use word boundaries (\b) to match whole words and escape for special characters
                if re.search(rf"\b{re.escape(pe_firm.lower())}\b", owner_text.lower()):
                    company_data["is_pe_owned"] = True
                    company_data["pe_owner_names"].append(pe_firm)
            
            # Additional keywords for ownership types (can be refined)
            if re.search(r'\b(?:family|founder|individual|private investor)\b', owner_text.lower()):
                potential_owners.append("Family/Private Individuals")
            if re.search(r'\b(?:institutional investor|pension fund|sovereign wealth fund)\b', owner_text.lower()):
                potential_owners.append("Institutional Investors")
            if re.search(r'\b(?:investment banking|venture capital)\b', owner_text.lower()):
                potential_owners.append("Investment Firms/VC")

            # If no specific PE firms found but other owners were mentioned, use those
            if not company_data["is_pe_owned"] and potential_owners:
                company_data["ownership_structure"] = ", ".join(list(set(potential_owners)))
            elif company_data["is_pe_owned"]:
                # If PE owned, add specific PE names to ownership structure if not already there
                existing_owners = [o.strip() for o in company_data["ownership_structure"].split(',') if o.strip()]
                all_owners = list(set(company_data["pe_owner_names"] + existing_owners))
                company_data["ownership_structure"] = ", ".join(all_owners)
            
            # Heuristic for flagging PE account: if any known PE firm is an owner
            # As per requirement: "If its more than 50% ownership by a Private Equity then we would need to flag it as PE account"
            # We assume for now that if any PE is identified as an owner, it implies significant ownership.
            # A true >50% check would require specific data not easily available from general search snippets.
            if company_data["is_pe_owned"]:
                company_data["flagged_as_pe_account"] = True


        # 4. Revenue
        # Pattern to capture currency, amount, unit, and an optional year in parentheses
        revenue_match = re.search(
            r"(?:revenue|annual revenue|turnover):\s*(\$|€|£)?\s*([\d\.,]+)\s*(?:million|billion|k|M|B|trillion)?\s*(?:year\s*)?\(?(\d{4})?\)?",
            gemini_text_response, re.IGNORECASE
        )
        if revenue_match:
            currency = revenue_match.group(1) if revenue_match.group(1) else ""
            amount = revenue_match.group(2).replace(",", "").replace(".", "")
            unit = revenue_match.group(3) if revenue_match.group(3) else ""
            year = revenue_match.group(4) if revenue_match.group(4) else "N/A"
            
            if unit.lower() == 'k': unit = 'thousand'
            elif unit.lower() == 'm': unit = 'million'
            elif unit.lower() == 'b': unit = 'billion'
            
            company_data["revenue"] = f"{currency}{amount} {unit}".strip()
            company_data["revenue_year"] = year

        # 5. Employees
        # Pattern to capture amount and an optional year in parentheses
        employees_match = re.search(
            r"(?:employees|staff|workforce|headcount):\s*([\d\.,]+)\s*(?:employees)?\s*(?:year\s*)?\(?(\d{4})?\)?",
            gemini_text_response, re.IGNORECASE
        )
        if employees_match:
            company_data["employees"] = employees_match.group(1).replace(",", "")
            company_data["employees_year"] = employees_match.group(2) if employees_match.group(2) else "N/A"

        # 6. Nation (Headquarters)
        nation_match = re.search(r"nation \(headquarters\):\s*([A-Za-z\s-]+(?:, [A-Za-z\s-]+)?)", gemini_text_response, re.IGNORECASE)
        if nation_match:
            company_data["nation"] = nation_match.group(1).strip()
        else: # Fallback: try to find common nations in the text if explicit pattern is missed
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
        logging.error(f"Error analyzing {company_name} with Gemini: {e}", exc_info=True) # exc_info to print stack trace
        company_data["error"] = str(e)

    logging.info(f"Finished analysis for {company_name}. Data: {company_data}")
    return company_data

def process_companies_in_background(companies_df: pd.DataFrame, report_id: str, report_name: str, gemini_api_key: str, pe_firms_list: list) -> None:
    """
    Background task to process companies from a DataFrame and save the final report.
    This function is designed to be run in a separate thread.

    Args:
        companies_df: Pandas DataFrame containing company names.
        report_id: Unique identifier for the report.
        report_name: Human-readable name for the report.
        gemini_api_key: API key for Gemini.
        pe_firms_list: List of known PE firms.
    """

    start_time = datetime.now() # Record start time
    logging.info(f"Background analysis for report ID {report_id} started at {start_time}.")

    results = []
    total_companies = len(companies_df)
    
    # Iterate through each company name in the DataFrame's 'Company Name' column
    # Use .iterrows() for safe iteration if you need index and row, though just .values is faster for a single column
    for i, company_name in enumerate(companies_df['Company Name'].values):
        if pd.isna(company_name) or str(company_name).strip() == "":
            logging.warning(f"Skipping empty company name at index {i}.")
            continue
        company_name_str = str(company_name).strip() # Ensure it's a string and clean whitespace

        logging.info(f"Processing {i+1}/{total_companies}: {company_name_str}")
        
        # Analyze each company using the dedicated analysis function
        data = analyze_company(company_name_str, gemini_api_key, pe_firms_list)
        results.append(data)

    end_time = datetime.now() # Record end time
    duration = end_time - start_time
    duration_seconds = duration.total_seconds() # Get duration in seconds
    logging.info(f"Background analysis for report ID {report_id} completed at {end_time}. Duration: {duration}.")

    # Define the path where the completed report will be saved
    # Define the path where the completed report will be saved
    report_data = {
        "report_name": report_name,
        "data": results,
        "analysis_duration_seconds": duration_seconds, # NEW: Add duration to report data
        "analysis_start_time": start_time.isoformat(),
        "analysis_end_time": end_time.isoformat()
    }
    report_path = os.path.join(config.REPORTS_FOLDER, f'{report_id}.json')
    utils.save_json_file(report_path, report_data)
    
    # Update the analysis history with the completion status
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
            "date": start_time.isoformat(), # Use the actual start time from this function's scope
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

    # Generate a unique ID and a human-readable name for the new report
    report_id = str(uuid.uuid4())
    report_name = f"Analysis Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # Create a "Pending" entry in the analysis history immediately
    history = utils.load_history()
    history_entry = {
        "id": report_id,
        "name": report_name,
        "date": datetime.now().isoformat(), # The time the analysis was initiated
        "status": "Pending",
        "num_companies": len(companies_df),
        "file_path": None,
        "completed_at": None,
        "analysis_duration_seconds": None
    }
    history.insert(0, history_entry)
    utils.save_history(history)
    
    # Start the company analysis as a background thread.
    # This is crucial so the web server remains responsive while analysis runs.
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


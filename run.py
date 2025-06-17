import os
import json
import pandas as pd
from flask import Flask, request, jsonify, render_template, send_from_directory
from datetime import datetime
import threading
import uuid
import logging
import re

# Import the Google Generative AI library
import google.generativeai as genai

# Configure logging to see what's happening in the console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize the Flask application
app = Flask(__name__, static_folder='static', template_folder='templates')

# Define paths for various application components
UPLOAD_FOLDER = 'uploads'
REPORTS_FOLDER = 'reports'
SETTINGS_FILE = 'settings.json'
HISTORY_FILE = 'history.json'
PE_LIST_FILE = 'pe_firms.json'

# Ensure that the necessary directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

# --- Utility Functions ---

def load_settings():
    """Loads API keys and other settings from a JSON file."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON from {SETTINGS_FILE}. Returning empty settings.")
            return {}
    return {}

def save_settings(settings):
    """Saves API keys and other settings to a JSON file."""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

def load_history():
    """Loads analysis history from a JSON file."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON from {HISTORY_FILE}. Returning empty history.")
            return []
    return []

def save_history(history):
    """Saves analysis history to a JSON file."""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)

def load_pe_firms():
    """Loads the list of private equity firms."""
    if os.path.exists(PE_LIST_FILE):
        try:
            with open(PE_LIST_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON from {PE_LIST_FILE}. Initializing with default PE firms.")
            default_pe_firms = get_default_pe_firms()
            save_pe_firms(default_pe_firms)
            return default_pe_firms
    else:
        default_pe_firms = get_default_pe_firms()
        save_pe_firms(default_pe_firms)
        return default_pe_firms

def get_default_pe_firms():
    """Returns a default list of private equity firms."""
    return [
        "Blackstone", "KKR", "Carlyle Group", "Apollo Global Management",
        "TPG Capital", "Advent International", "Warburg Pincus", "Permira",
        "Thoma Bravo", "Silver Lake", "General Atlantic", "Ardian",
        "EQT Partners", "Partners Group", "Cinven", "Bain Capital",
        "Vista Equity Partners", "Hellman & Friedman", "Insight Partners",
        "CVC Capital Partners", "Leonard Green & Partners",
        "GIC (Government of Singapore Investment Corporation)", "Temasek Holdings",
        "Abu Dhabi Investment Authority (ADIA)", "Qatar Investment Authority (QIA)",
        "SoftBank Vision Fund", "Goldman Sachs Principal Investments",
        "Morgan Stanley Capital Partners", "J.P. Morgan Asset Management Private Equity",
        "Lion Capital", "Apax Partners", "Bridgepoint", "Clayton Dubilier & Rice",
        "Francisco Partners", "GTCR", "Hg", "Madison Dearborn Partners",
        "Nordic Capital", "PAI Partners", "Platinum Equity", "Riverside Company",
        "Roark Capital Group"
    ]

def save_pe_firms(pe_firms):
    """Saves the list of private equity firms."""
    with open(PE_LIST_FILE, 'w') as f:
        json.dump(pe_firms, f, indent=4)

def analyze_company(company_name, gemini_api_key, pe_firms_list):
    """
    Analyzes a company using Gemini with search grounding to get information.
    """
    logging.info(f"Analyzing company: {company_name}")
    company_data = {
        "company_name": company_name,
        "ownership_structure": "N/A",
        "public_private": "Unknown",
        "is_pe_owned": False,
        "pe_owner_names": [],
        "is_itself_pe": False,
        "revenue": "N/A",
        "employees": "N/A",
        "nation": "Unknown",
        "flagged_as_pe_account": False,
        "source_snippets": [],
        "error": None
    }

    try:
        # Configure Gemini API
        genai.configure(api_key=gemini_api_key)
        
        # Initialize the GenerativeModel.
        # Use a model that supports tool calling, like 'gemini-pro'.
        # Note: The availability and exact naming of models might vary.
        # Check https://ai.google.dev/models for the latest.
        model = genai.GenerativeModel('gemini-pro') 

        # Craft a precise prompt for Gemini, instructing it to use search
        # and extract specific information.
        prompt = (
            f"Find the following information for the company '{company_name}':\n"
            "1. Is it publicly traded or privately owned? (State 'Public' or 'Private')\n"
            "2. If private, identify its main owners, including any Private Equity firms, Investment banking owned PEs, Institutional investors, Pension funds, or Family funds. List the names.\n"
            "3. Is the company itself a Private Equity firm? (State 'Yes' or 'No')\n"
            "4. What is its approximate annual revenue?\n"
            "5. How many employees does it have?\n"
            "6. Which nation is its headquarters located in?\n"
            "Provide concise answers for each point based on your search results. Include relevant snippets or URLs if possible."
        )

        # Generate content, allowing Gemini to use Google Search as a tool
        # The tool_code.GoogleSearch() allows Gemini to perform web searches internally.
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

        # Get the text content from the Gemini response
        # The response structure can vary, so we handle potential errors.
        try:
            gemini_text_response = response.text
        except ValueError: # If response.text is not available, maybe there's a prompt feedback
            logging.warning(f"Gemini response.text not available for {company_name}. Content: {response.parts}")
            gemini_text_response = str(response.parts) # Fallback to string representation of parts

        # Collect source snippets provided by Gemini's grounding
        if response.prompt_feedback and response.prompt_feedback.grounding_attributions:
            for attribution in response.prompt_feedback.grounding_attributions:
                if attribution.web_uri:
                    company_data["source_snippets"].append({
                        "snippet": attribution.snippet,
                        "url": attribution.web_uri,
                        "source_title": attribution.title
                    })
        elif hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'grounding_attributions') and candidate.grounding_attributions:
                    for attribution in candidate.grounding_attributions:
                        if hasattr(attribution, 'uri'): # Newer structure might have 'uri'
                            company_data["source_snippets"].append({
                                "snippet": attribution.content,
                                "url": attribution.uri,
                                "source_title": attribution.title
                            })


        # --- Information Extraction from Gemini's Text Response ---
        # We'll use regex and keyword matching on Gemini's summarized text
        # for structured data extraction. This is more reliable as Gemini has
        # already processed the raw search results.

        response_lower = gemini_text_response.lower()

        # 1. Public vs Private
        if "public" in response_lower and "publicly traded" in response_lower:
            company_data["public_private"] = "Public"
        elif "private" in response_lower and ("privately owned" in response_lower or "privately held" in response_lower):
            company_data["public_private"] = "Private"

        # 2. Private Equity Ownership and Ownership Structure
        # Check if the company itself is a PE firm
        if "private equity firm: yes" in response_lower or "is a private equity firm" in response_lower:
            company_data["is_itself_pe"] = True
            company_data["public_private"] = "Private" # PE firms are typically private

        # Identify PE owners
        identified_pe_owners = []
        for pe_firm in pe_firms_list:
            # Look for PE firm names in the response
            if pe_firm.lower() in response_lower:
                # To be more precise, look for "owned by [PE Firm]" or "[PE Firm] acquired"
                if re.search(rf"(owned by|backed by|acquired by|investment from)\s*{re.escape(pe_firm.lower())}", response_lower):
                    identified_pe_owners.append(pe_firm)
        
        if identified_pe_owners:
            company_data["is_pe_owned"] = True
            company_data["pe_owner_names"] = list(set(identified_pe_owners)) # Remove duplicates

            # Flag as PE account if any PE ownership is detected.
            # Real 50%+ ownership check requires more than public snippets.
            # "If its more than 50% ownership by a Private Equity then we would need to flag it as PE account"
            # For this version, detecting *any* PE ownership will flag it. This can be refined.
            company_data["flagged_as_pe_account"] = True

        # Extract general ownership structure if not PE owned and private
        if company_data["public_private"] == "Private" and not company_data["is_pe_owned"]:
            owner_match = re.search(r"(owned by|controlled by|major investor[s]?:)\s*([A-Za-z0-9\s,&\.]+(?: family|group|fund|llc|inc|corp|holdings|investment|trust|ventures|partners|capital|institutional investor|pension fund|family office|venture capital)?)", gemini_text_response, re.IGNORECASE)
            if owner_match:
                company_data["ownership_structure"] = owner_match.group(2).strip()
            elif "family owned" in response_lower:
                company_data["ownership_structure"] = "Family-owned"


        # 3. Revenue
        revenue_match = re.search(r"(?:revenue of|annual revenue around|earns about|generates about)\s*(\$|€|£)?\s*([\d\.,]+)\s*(million|billion|M|B)?", gemini_text_response, re.IGNORECASE)
        if revenue_match:
            amount = revenue_match.group(2).replace(",", "")
            unit = revenue_match.group(3) if revenue_match.group(3) else ""
            currency = revenue_match.group(1) if revenue_match.group(1) else ""
            company_data["revenue"] = f"{currency}{amount} {unit}".strip()

        # 4. Employees
        employees_match = re.search(r"([\d\.,]+)\s*(employees|staff|people|headcount)", gemini_text_response, re.IGNORECASE)
        if employees_match:
            company_data["employees"] = employees_match.group(1).replace(",", "")

        # 5. Nation (Headquarters)
        nations = [
            "Switzerland", "Germany", "France", "UK", "United Kingdom", "USA", "United States", "Canada",
            "China", "India", "Japan", "Australia", "Italy", "Spain", "Netherlands", "Belgium",
            "Sweden", "Norway", "Denmark", "Finland", "Austria", "Ireland", "Portugal",
            "Singapore", "South Korea", "Brazil", "Mexico", "South Africa", "UAE", "United Arab Emirates",
            "Luxembourg", "Ireland", "Cayman Islands", "Jersey", "Guernsey" # Added common PE firm locations
        ]
        
        found_nation = "Unknown"
        # Look for "headquartered in [Nation]" or similar phrases first
        hq_pattern = r"headquartered in (the )?([\w\s-]+(?:, [\w\s-]+)?)\."
        hq_match = re.search(hq_pattern, gemini_text_response, re.IGNORECASE)
        if hq_match:
            location_str = hq_match.group(2).strip().lower()
            for nation in nations:
                if nation.lower() in location_str:
                    found_nation = nation
                    break
        
        if found_nation == "Unknown": # Fallback to general nation detection
            for nation in nations:
                if nation.lower() in response_lower or f"{nation.lower()}-based" in response_lower:
                    found_nation = nation
                    break
        company_data["nation"] = found_nation

    except genai.types.BlockedPromptException as e:
        logging.error(f"Gemini API blocked prompt for {company_name}: {e}")
        company_data["error"] = f"Gemini API blocked prompt: {e.response.prompt_feedback.block_reason.name}"
    except Exception as e:
        logging.error(f"Error analyzing {company_name} with Gemini: {e}")
        company_data["error"] = str(e)

    return company_data

def process_companies_task(companies_df, report_id, report_name, gemini_api_key, pe_firms_list):
    """Background task to process companies and save the report."""
    results = []
    total_companies = len(companies_df)
    for i, company_name in enumerate(companies_df['Company Name']):
        logging.info(f"Processing {i+1}/{total_companies}: {company_name}")
        data = analyze_company(company_name, gemini_api_key, pe_firms_list)
        results.append(data)

    report_path = os.path.join(REPORTS_FOLDER, f'{report_id}.json')
    with open(report_path, 'w') as f:
        json.dump({"report_name": report_name, "data": results}, f, indent=4)

    # Update history
    history = load_history()
    for entry in history:
        if entry['id'] == report_id:
            entry["status"] = "Completed"
            entry["file_path"] = report_path
            break
    save_history(history)
    logging.info(f"Report '{report_name}' (ID: {report_id}) saved.")


# --- Flask Routes ---

@app.route('/')
def index():
    """Renders the main page."""
    return render_template('index.html')

@app.route('/settings', methods=['GET', 'POST'])
def handle_settings():
    """Handles saving and loading of application settings."""
    if request.method == 'POST':
        settings_data = request.json
        
        gemini_api_key = settings_data.get('gemini_api_key')
        current_settings = load_settings()
        current_settings['gemini_api_key'] = gemini_api_key
        save_settings(current_settings)

        pe_firms_list = settings_data.get('pe_firms')
        if pe_firms_list is not None and isinstance(pe_firms_list, list):
            save_pe_firms(pe_firms_list)
        else:
            logging.warning("PE firms list not provided or in invalid format during settings update.")

        logging.info("Settings updated.")
        return jsonify({"message": "Settings updated successfully!"})
    else: # GET request
        settings = load_settings()
        pe_firms = load_pe_firms()
        settings['pe_firms'] = pe_firms
        return jsonify(settings)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles the upload of the Excel file and triggers analysis."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        if file_extension not in ['xlsx', 'xls']:
            return jsonify({"error": "Invalid file type. Please upload an Excel file (.xlsx or .xls)."}), 400

        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(filepath)
        logging.info(f"File '{file.filename}' uploaded to {filepath}")

        try:
            companies_df = pd.read_excel(filepath)
            if 'Company Name' not in companies_df.columns:
                return jsonify({"error": "Excel file must contain a 'Company Name' column."}), 400

            company_names = companies_df['Company Name'].dropna().tolist()
            if not company_names:
                return jsonify({"error": "No valid company names found in the 'Company Name' column."}), 400
            
            settings = load_settings()
            gemini_api_key = settings.get('gemini_api_key')
            pe_firms_list = load_pe_firms()

            if not gemini_api_key:
                return jsonify({"error": "Gemini API Key is not configured. Please set it in settings."}), 400

            report_id = str(uuid.uuid4())
            report_name = f"Analysis Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            history = load_history()
            history_entry = {
                "id": report_id,
                "name": report_name,
                "date": datetime.now().isoformat(),
                "status": "Pending",
                "num_companies": len(company_names),
                "file_path": None
            }
            history.insert(0, history_entry)
            save_history(history)
            
            thread = threading.Thread(
                target=process_companies_task,
                args=(companies_df, report_id, report_name, gemini_api_key, pe_firms_list)
            )
            thread.start()

            return jsonify({
                "message": "File uploaded and analysis started! You can check the history for status.",
                "report_id": report_id,
                "report_name": report_name
            }), 200

        except pd.errors.EmptyDataError:
            return jsonify({"error": "The Excel file is empty."}), 400
        except pd.errors.ParserError:
            return jsonify({"error": "Could not parse Excel file. Ensure it is a valid .xlsx or .xls."}), 400
        except Exception as e:
            logging.error(f"Error processing uploaded file: {e}")
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

@app.route('/history')
def get_history():
    """Returns the analysis history."""
    history = load_history()
    return jsonify(history)

@app.route('/report/<report_id>')
def get_report(report_id):
    """Returns a specific analysis report."""
    report_path = os.path.join(REPORTS_FOLDER, f'{report_id}.json')
    if os.path.exists(report_path):
        with open(report_path, 'r') as f:
            report_data = json.load(f)
        return jsonify(report_data)
    logging.warning(f"Report with ID {report_id} not found at {report_path}")
    return jsonify({"error": "Report not found"}), 404

@app.route('/status/<report_id>')
def get_report_status(report_id):
    """Checks the status of a specific report."""
    history = load_history()
    for entry in history:
        if entry['id'] == report_id:
            return jsonify({"status": entry['status']})
    return jsonify({"status": "Unknown"}), 404

@app.route('/pe_firms', methods=['POST'])
def update_pe_firms():
    """Updates the list of private equity firms."""
    pe_firms = request.json.get('pe_firms', [])
    if not isinstance(pe_firms, list):
        return jsonify({"error": "Invalid format for PE firms. Must be a list."}), 400
    save_pe_firms(pe_firms)
    logging.info("PE firms list updated.")
    return jsonify({"message": "Private Equity firms list updated successfully!"})

if __name__ == '__main__':
    load_pe_firms() # Ensure default PE firms are loaded/saved on startup
    logging.info("Starting Flask application...")
    app.run(debug=True, port=5000)

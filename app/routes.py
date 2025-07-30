import pandas as pd
import uuid
from flask import Blueprint, request, jsonify, render_template, current_app, send_file
import logging
from . import services
from . import utils
import os

# Create a Blueprint for our application's routes
main_bp = Blueprint('main', __name__)

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


@main_bp.route('/')
def index():
    """
    Renders the main HTML page (index.html).
    This is the default route when accessing the root URL.
    """
    return render_template('index.html')

@main_bp.route('/settings', methods=['GET', 'POST'])
def handle_settings():
    """
    Handles API requests for application settings.
    GET: Retrieves current settings (including Gemini API key and PE firms list).
    POST: Updates settings.
    """
    if request.method == 'POST':
        settings_data = request.json
        if not settings_data:
            return jsonify({"error": "No settings data provided."}), 400

        # Extract and save Gemini API key
        gemini_api_key = settings_data.get('gemini_api_key')
        current_settings = utils.load_settings()
        current_settings['gemini_api_key'] = gemini_api_key
        utils.save_settings(current_settings)

        # Extract and save PE firms list
        pe_firms_list = settings_data.get('pe_firms')
        if pe_firms_list is not None and isinstance(pe_firms_list, list):
            utils.save_pe_firms(pe_firms_list)
        else:
            logging.warning("PE firms list not provided or in invalid format during settings update. Keeping existing list.")

        return jsonify({"message": "Settings updated successfully!"}), 200
    else: # GET request gets also the api key, ONLY FOR LOCAL USE
        settings = utils.load_settings()
        pe_firms = utils.load_pe_firms()
        settings['pe_firms'] = pe_firms
        return jsonify(settings), 200

@main_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    Handles the upload of the Excel file, extracts company names,
    and triggers the background analysis.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    # Check if the file type is allowed
    if not utils.allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Please upload an Excel file (.xlsx or .xls)."}), 400

    if file:
        # Create a unique filename to prevent overwriting issues, especially in background tasks
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        logging.info(f"File '{file.filename}' uploaded to {filepath}")

        try:
            # Read the Excel file into a pandas DataFrame
            companies_df = pd.read_excel(filepath)
            
            # Ensure the required 'Company Name' column exists
            if 'Company Name' not in companies_df.columns:
                return jsonify({"error": "Excel file must contain a 'Company Name' column."}), 400

            # Get the list of company names, dropping any empty or NaN entries
            company_names = companies_df['Company Name'].dropna().tolist()
            if not company_names:
                return jsonify({"error": "No valid company names found in the 'Company Name' column."}), 400
            
            # Call the service layer to start the analysis
            analysis_status = services.start_company_analysis(companies_df, filepath)
            
            if "error" in analysis_status:
                return jsonify(analysis_status), 500 # Return error from service
            else:
                return jsonify(analysis_status), 200

        except pd.errors.EmptyDataError:
            return jsonify({"error": "The Excel file is empty."}), 400
        except pd.errors.ParserError:
            return jsonify({"error": "Could not parse Excel file. Ensure it is a valid .xlsx or .xls."}), 400
        except Exception as e:
            logging.error(f"Error processing uploaded file: {e}", exc_info=True)
            return jsonify({"error": f"An unexpected error occurred during file processing: {e}"}), 500

@main_bp.route('/history')
def get_history():
    """
    Returns the analysis history.
    """
    history = utils.load_history()
    return jsonify(history), 200

@main_bp.route('/status/<report_id>')
def get_report_status(report_id):
    """
    Checks and returns the current status (Pending/Completed) of a specific report.
    """
    history = utils.load_history()
    for entry in history:
        if entry['id'] == report_id:
            return jsonify({"status": entry['status']}), 200
    return jsonify({"status": "Unknown"}), 404

@main_bp.route('/pe_firms', methods=['GET', 'POST'])
def handle_pe_firms():
    """
    Handles GET and POST requests for the Private Equity firms list.
    GET: Returns the current list.
    POST: Updates the list.
    """
    if request.method == 'POST':
        pe_firms = request.json.get('pe_firms', [])
        if not isinstance(pe_firms, list):
            return jsonify({"error": "Invalid format for PE firms. Must be a list."}), 400
        utils.save_pe_firms(pe_firms)
        return jsonify({"message": "Private Equity firms list updated successfully!"}), 200
    else: # GET request
        pe_firms = utils.load_pe_firms()
        return jsonify(pe_firms), 200

@main_bp.route('/download/<report_id>')
def download_report(report_id):
    """
    Generates and serves the Excel report for download.
    """
    filepath = services.create_downloadable_report(report_id)
    
    if filepath and os.path.exists(filepath):
        try:
            return send_file(
                filepath,
                as_attachment=True,
                download_name=f"Analysis_Report_{report_id}.xlsx"
            )
        except Exception as e:
            logging.error(f"Error sending file for report ID {report_id}: {e}", exc_info=True)
            return jsonify({"error": "Could not send the file."}), 500
    else:
        return jsonify({"error": "Report not found or could not be generated."}), 

@main_bp.route('/report/<report_id>', methods=['GET', 'DELETE'])
def handle_report(report_id):
    """
    Handles GETting or DELETEing a specific report.
    """
    if request.method == 'DELETE':
        success = services.delete_report(report_id)
        if success:
            return jsonify({"message": "Report deleted successfully"}), 200
        else:
            return jsonify({"error": "Report not found or could not be deleted"}), 404
    
    # This is the original GET logic
    report_path = os.path.join(current_app.config['REPORTS_FOLDER'], f'{report_id}.json')
    
    if not os.path.exists(report_path):
        logging.warning(f"Report with ID {report_id} not found at {report_path}")
        return jsonify({"error": "Report not found"}), 404
    
    try:
        report_data = utils.load_json_file(report_path)
        if not report_data:
            return jsonify({"error": "Report data is empty or corrupt."}), 500
        return jsonify(report_data), 200
    except Exception as e:
        logging.error(f"Error loading report {report_id} from {report_path}: {e}", exc_info=True)
        return jsonify({"error": f"Failed to load report data: {e}"}), 500
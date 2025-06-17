import os
import logging
from flask import Flask
from . import config
from . import utils
from .routes import main_bp 

# Configure logging for the application
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_app():
    """
    Flask application factory function.
    Initializes the Flask app, configures it, and registers blueprints.
    """
    app = Flask(__name__,
                template_folder=config.TEMPLATES_FOLDER,
                static_folder=config.STATIC_FOLDER)

    # Load configuration from config.py
    app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
    app.config['REPORTS_FOLDER'] = config.REPORTS_FOLDER
    app.config['SETTINGS_FILE'] = config.SETTINGS_FILE
    app.config['HISTORY_FILE'] = config.HISTORY_FILE
    app.config['PE_LIST_FILE'] = config.PE_LIST_FILE
    app.config['ALLOWED_EXTENSIONS'] = config.ALLOWED_EXTENSIONS
    
    # Ensure necessary directories exist on app startup
    utils.ensure_dirs()
    
    # Initialize default PE firms list if it doesn't exist
    utils.load_pe_firms()
    
    app.register_blueprint(main_bp)

    logging.info("Flask application created and configured.")
    return app

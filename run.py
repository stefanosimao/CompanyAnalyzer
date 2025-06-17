import logging
from app import create_app 

# Configure logging for the main entry point
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == '__main__':
    # Create the Flask application instance using the factory function
    app = create_app()
    
    logging.info("Starting Flask development server...")
    # Run the Flask development server.
    app.run(debug=True, port=5000)

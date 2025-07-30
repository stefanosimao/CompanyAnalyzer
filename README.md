# Company Ownership Analyzer (PE Hunter)

## 📖 Overview

The **Company Ownership Analyzer**, also known as **PE Hunter**, is a powerful tool designed to automate the research of company ownership structures. This application takes a list of company names from an Excel file, analyzes each one to determine its ownership category (e.g., Private Equity-owned, Public, Family-owned), and identifies its key PE owners.

The tool is built with a **Flask** backend that uses the **Google Gemini API** for its AI-powered analysis and a modern **React** frontend with **Material-UI** for a clean and intuitive user experience.

### Key Features:

- **Bulk Analysis**: Upload an Excel file with a list of company names to analyze them in batches.
- **AI-Powered Insights**: Leverages the Gemini API to research and categorize company ownership structures.
- **Detailed Reports**: View comprehensive reports with visualizations, including ownership category breakdowns and top headquarters nations.
- **PE Firm Discovery**: Automatically discovers new Private Equity firms and can research their portfolios.
- **History Tracking**: Keeps a history of all analysis reports, showing their status and results.

---

## Tech Stack

- **Backend**: Python, Flask, Pandas
- **Frontend**: React, Vite, Material-UI, Recharts
- **AI Engine**: Google Gemini API

---

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- **Python** (3.9 or higher)
- **Node.js** and **npm** (for the frontend)
- A **Google Gemini API Key**

### Installation and Setup

**1. Clone the repository:**

```bash
git clone [https://github.com/stefanosimao/companyanalyzer.git](https://github.com/stefanosimao/companyanalyzer.git)
cd companyanalyzer
```

**2. Backend Setup:**
First, create and activate a Python virtual environment to keep dependencies isolated:
```bash
python3 -m venv venv
source venv/bin/activate
```
On Windows, use: `venv\Scripts\activate`

Next, create a requirements.txt file in the root of the project with the following content:
```Bash
flask
pandas
openpyxl
google-generativeai
python-dotenv
```

Then, install the required Python packages:
```bash
pip install -r requirements.txt
```

**3. Frontend Setup:**
Navigate to the frontend directory and install the necessary npm packages:
cd frontend
npm install
```

**4. Configure Environment Variables:**
Create a .env file in the root of the project directory. This file will securely store your API key.
```bash
GEMINI_API_KEY="your_actual_api_key_here"
```

Note: The .gitignore file is already configured to ignore the .env file, so your API key will not be committed to version control.

## Running the Application

You will need to run the backend and frontend servers in separate terminals.
**Terminal 1: Start the Backend (Flask Server)**
```bash
From the root of the project directory:
python run.py
```

The Flask server will start on http://127.0.0.1:5000.
**Terminal 2: Start the Frontend (Vite Dev Server)**
```bash
From the frontend directory:
npm run dev
```

The React development server will start on http://127.0.0.1:5173.

Now, you can open your web browser and navigate to http://127.0.0.1:5173 to use the application. The frontend is set up to proxy API requests to the backend Flask server.

##Usage

1. Navigate to the "New Analysis" page.
2. Upload an Excel file containing a single column with the header Company Name.
3. Click "Start Analysis".
4. You will be redirected to the "History" page, where you can monitor the progress of your report.
5. Once completed, click on the report to view the detailed analysis and visualizations.
````

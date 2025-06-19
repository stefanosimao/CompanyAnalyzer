import React, { useState, useEffect } from 'react';
import { format } from 'date-fns'; 
import UploadSection from './components/UploadSection';
import SettingsSection from './components/SettingsSection';
import HistorySection from './components/HistorySection';
import ReportDetailSection from './components/ReportDetailSection';
import PEInsightsSection from './components/PEInsightsSection'

function App() {
  // State to manage the currently active section in the UI, 'upload' will be the default view
  const [activeSection, setActiveSection] = useState('upload');
  const [currentReportId, setCurrentReportId] = useState(null); // Stores the ID of the report being viewed
  const [currentPEFirm, setCurrentPEFirm] = useState(null);   // Stores the name of the PE firm being viewed

  // State for global message/alert display
  const [message, setMessage] = useState({ type: '', text: '' });

  // Function to display messages/alerts
  const showAlert = (type, text, duration = 5000) => {
    setMessage({ type, text });
    setTimeout(() => setMessage({ type: '', text: '' }), duration);
  };

  // Function to navigate between sections
  const navigateTo = (section, reportId = null, peFirm = null) => {
    setActiveSection(section);
    setCurrentReportId(reportId);
    setCurrentPEFirm(peFirm);
  };

  // Render the main application structure
  return (
    <div className="min-h-screen flex flex-col items-center p-4 sm:p-6 lg:p-8">
      {/* Main Application Container */}
      <div className="bg-white shadow-xl rounded-xl w-full max-w-7xl flex flex-col lg:flex-row overflow-hidden min-h-[90vh]">

        {/* Sidebar Navigation (Left Panel) */}
        <aside className="w-full lg:w-64 bg-gray-800 text-white p-6 flex flex-col justify-between rounded-t-xl lg:rounded-l-xl lg:rounded-tr-none">
          <div>
            <h1 className="text-3xl font-bold mb-8 text-center sm:text-left">PE Hunter</h1>
            <nav className="space-y-4">
              <button
                className={`nav-button w-full flex items-center justify-center lg:justify-start px-4 py-3 rounded-lg text-lg font-medium text-left transition-all duration-200 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 ${activeSection === 'upload' ? 'active-nav' : ''}`}
                onClick={() => navigateTo('upload')}
              >
                <i className="ph ph-upload-simple mr-3 text-2xl"></i>
                <span className="hidden lg:inline">Upload File</span>
              </button>
              <button
                className={`nav-button w-full flex items-center justify-center lg:justify-start px-4 py-3 rounded-lg text-lg font-medium text-left transition-all duration-200 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 ${activeSection === 'settings' ? 'active-nav' : ''}`}
                onClick={() => navigateTo('settings')}
              >
                <i className="ph ph-gear-six mr-3 text-2xl"></i>
                <span className="hidden lg:inline">Settings</span>
              </button>
              <button
                className={`nav-button w-full flex items-center justify-center lg:justify-start px-4 py-3 rounded-lg text-lg font-medium text-left transition-all duration-200 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 ${activeSection === 'history' || activeSection === 'reportDetail' || activeSection === 'peInsights' ? 'active-nav' : ''}`}
                onClick={() => navigateTo('history')}
              >
                <i className="ph ph-clock-counter-clockwise mr-3 text-2xl"></i>
                <span className="hidden lg:inline">History</span>
              </button>
            </nav>
          </div>
          <div className="mt-8 text-center text-sm text-gray-400 hidden lg:block">
            <p>&copy; 2024 PE Hunter</p>
            <p>Developed by Gemini</p>
            <p>For Tata Consultancy Services</p>
          </div>
        </aside>

        {/* Main Content Area (Right Panel) */}
        <main className="flex-1 p-6 sm:p-8 lg:p-10 bg-gray-50 rounded-b-xl lg:rounded-r-xl lg:rounded-bl-none overflow-y-auto">
          {/* Global Message/Alert Area */}
          {message.text && (
            <div id="message-area" className="mb-6 animate-fade-in">
              <div
                className={`border-l-4 p-4 rounded-md shadow-sm ${
                  message.type === 'error' ? 'bg-red-100 border-red-500 text-red-700' :
                  message.type === 'success' ? 'bg-green-100 border-green-500 text-green-700' :
                  'bg-blue-100 border-blue-500 text-blue-700'
                }`}
                role="alert"
              >
                <p className="font-bold">{message.type.charAt(0).toUpperCase() + message.type.slice(1)}</p>
                <p>{message.text}</p>
              </div>
            </div>
          )}

          {/* Conditional Rendering of Sections */}
          {activeSection === 'upload' && <UploadSection showAlert={showAlert} navigateTo={navigateTo} />}
          {activeSection === 'settings' && <SettingsSection showAlert={showAlert} />}
          {activeSection === 'history' && <HistorySection showAlert={showAlert} navigateTo={navigateTo} />}
          {activeSection === 'reportDetail' && currentReportId && (
            <ReportDetailSection
              reportId={currentReportId}
              showAlert={showAlert}
              navigateTo={navigateTo}
            />
          )}
          {activeSection === 'peInsights' && currentPEFirm && (
            <PEInsightsSection
              peFirmName={currentPEFirm}
              reportId={currentReportId}
              showAlert={showAlert}
              navigateTo={navigateTo}
            />
          )}

        </main>
      </div>
    </div>
  );
}

export default App;
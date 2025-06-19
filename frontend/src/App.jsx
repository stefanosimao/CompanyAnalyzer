import React, { useState } from 'react';
import UploadSection from './components/UploadSection';
import SettingsSection from './components/SettingsSection';
import HistorySection from './components/HistorySection';
import ReportDetailSection from './components/ReportDetailSection';
import PEInsightsSection from './components/PEInsightsSection'

const NavIcon = ({ iconName, className }) => (
  <i className={`ph ph-${iconName} ${className}`}></i>
);

function App() {
  const [activeSection, setActiveSection] = useState('upload');
  const [currentReportId, setCurrentReportId] = useState(null);
  const [currentPEFirm, setCurrentPEFirm] = useState(null);
  const [message, setMessage] = useState({ type: '', text: '' });

  const showAlert = (type, text, duration = 5000) => {
    setMessage({ type, text });
    setTimeout(() => setMessage({ type: '', text: '' }), duration);
  };

  const navigateTo = (section, reportId = null, peFirm = null) => {
    setActiveSection(section);
    setCurrentReportId(reportId);
    setCurrentPEFirm(peFirm);
  };

  const navItems = [
    { id: 'upload', icon: 'upload-simple', text: 'Upload', sections: ['upload'] },
    { id: 'history', icon: 'clock-counter-clockwise', text: 'History', sections: ['history', 'reportDetail', 'peInsights'] },
    { id: 'settings', icon: 'gear-six', text: 'Settings', sections: ['settings'] },
  ];

  return (
    <div className="min-h-screen bg-secondary/50">
      <div className="flex h-screen">
        {/* Sidebar Navigation */}
        <aside className="w-20 lg:w-64 bg-background text-foreground border-r border-border flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-center lg:justify-start h-20 border-b border-border px-6">
              <NavIcon iconName="magic-wand" className="text-3xl text-primary" />
              <h1 className="text-2xl font-bold ml-3 hidden lg:block">PE Hunter</h1>
            </div>
            <nav className="space-y-2 p-4">
              {navItems.map(item => (
                <button
                  key={item.id}
                  className={`w-full nav-button ${item.sections.includes(activeSection) ? 'active-nav' : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'}`}
                  onClick={() => navigateTo(item.id)}
                >
                  <NavIcon iconName={item.icon} className="text-2xl" />
                  <span className="ml-4 hidden lg:inline">{item.text}</span>
                </button>
              ))}
            </nav>
          </div>
          <div className="p-4 border-t border-border text-center text-xs text-muted-foreground hidden lg:block">
            <p>&copy; 2024 Tata Consultancy Services</p>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 p-6 sm:p-8 lg:p-10 overflow-y-auto">
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
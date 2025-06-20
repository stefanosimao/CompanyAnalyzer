import React, { useState } from 'react';
import { createTheme, ThemeProvider, CssBaseline, Box, Drawer, AppBar, Toolbar, Typography, List, ListItem, ListItemButton, ListItemIcon, ListItemText } from '@mui/material';

// Import Phosphor icons if you still have the stylesheet linked in index.html, or use MUI icons
// For simplicity, we'll use string placeholders, but you'd replace them with actual icon components
// e.g., import UploadFileIcon from '@mui/icons-material/UploadFile';

import UploadSection from './components/UploadSection';
import SettingsSection from './components/SettingsSection';
import HistorySection from './components/HistorySection';
import ReportDetailSection from './components/ReportDetailSection';
import PEInsightsSection from './components/PEInsightsSection';

const drawerWidth = 240;

// A professional, modern theme for the application
const theme = createTheme({
  palette: {
    primary: {
      main: '#5E35B1', // A deep purple
    },
    secondary: {
      main: '#f4f6f8',
    },
    background: {
      default: '#f4f6f8',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: 'Inter, sans-serif',
    h1: { fontWeight: 700 },
    h2: { fontWeight: 700 },
    h3: { fontWeight: 600 },
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: '12px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
          border: '1px solid #e0e0e0',
        }
      }
    }
  }
});

function App() {
  const [activeSection, setActiveSection] = useState('upload');
  const [currentReportId, setCurrentReportId] = useState(null);
  const [currentPEFirm, setCurrentPEFirm] = useState(null);
  // Alerting can be handled by a more robust library like "notistack" in a real app
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
    { id: 'upload', text: 'New Analysis', icon: 'ph-upload-simple' },
    { id: 'history', text: 'History', icon: 'ph-clock-counter-clockwise' },
    { id: 'settings', text: 'Settings', icon: 'ph-gear-six' },
  ];

  const drawer = (
    <div>
      <Toolbar sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', px: [1], height: 80 }}>
         <i className="ph-fill ph-magic-wand text-4xl" style={{color: theme.palette.primary.main}}></i>
        <Typography variant="h5" component="h1" noWrap sx={{ ml: 2, fontWeight: 'bold' }}>
          PE Hunter
        </Typography>
      </Toolbar>
      <Box sx={{ overflow: 'auto', p: 2 }}>
        <List>
          {navItems.map((item) => (
            <ListItem key={item.id} disablePadding>
              <ListItemButton
                selected={activeSection === item.id || (activeSection.includes('report') && item.id === 'history') || (activeSection.includes('peInsights') && item.id === 'history')}
                onClick={() => navigateTo(item.id)}
                sx={{ borderRadius: '8px', mb: 1 }}
              >
                <ListItemIcon sx={{color: 'inherit'}}>
                   <i className={`ph ${item.icon} text-2xl`}></i>
                </ListItemIcon>
                <ListItemText primary={item.text} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Box>
    </div>
  );

  return (
    <ThemeProvider theme={theme}>
      <Box sx={{ display: 'flex' }}>
        <CssBaseline />
        <Drawer
          variant="permanent"
          sx={{
            width: drawerWidth,
            flexShrink: 0,
            [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box', borderRight: 'none', backgroundColor: '#fdfdfd' },
          }}
        >
          {drawer}
        </Drawer>
        <Box component="main" sx={{ flexGrow: 1, p: 3, bgcolor: 'background.default', height: '100vh', overflowY: 'auto' }}>
           {message.text && (
            <div id="message-area" style={{marginBottom: '24px'}}>
              <div
                style={{
                  borderLeft: `4px solid ${message.type === 'error' ? '#f44336' : '#4caf50'}`,
                  padding: '16px',
                  borderRadius: '4px',
                  backgroundColor: message.type === 'error' ? '#ffebee' : '#e8f5e9',
                  color: message.type === 'error' ? '#c62828' : '#2e7d32'
                }}
              >
                <p style={{fontWeight: 'bold'}}>{message.type.charAt(0).toUpperCase() + message.type.slice(1)}</p>
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
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;
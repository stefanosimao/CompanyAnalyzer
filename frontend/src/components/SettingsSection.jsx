import React, { useState, useEffect } from 'react';
import { Button, Card, CardContent, Typography, Box, CircularProgress, TextField, Alert } from '@mui/material';

function SettingsSection({ showAlert }) {
  const [geminiApiKey, setGeminiApiKey] = useState('');
  const [peFirms, setPeFirms] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [initialSettings, setInitialSettings] = useState(null);

  useEffect(() => {
    const fetchSettings = async () => {
      setIsLoading(true);
      try {
        const response = await fetch('/settings');
        const data = await response.json();
        if (response.ok) {
          const settings = {
            gemini_api_key: data.gemini_api_key || '',
            pe_firms: (data.pe_firms || []).join('\n')
          };
          setGeminiApiKey(settings.gemini_api_key);
          setPeFirms(settings.pe_firms);
          setInitialSettings(settings);
        } else {
          showAlert('error', data.error || 'Failed to load settings.');
        }
      } catch (error) {
        showAlert('error', `Network error while loading settings: ${error.message}`);
      } finally {
        setIsLoading(false);
      }
    };
    fetchSettings();
  }, [showAlert]);

  const hasChanges = useMemo(() => {
    if (!initialSettings) return false;
    return geminiApiKey !== initialSettings.gemini_api_key || peFirms !== initialSettings.pe_firms;
  }, [geminiApiKey, peFirms, initialSettings]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsSaving(true);
    showAlert('info', 'Saving settings...');
    try {
      const response = await fetch('/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          gemini_api_key: geminiApiKey,
          pe_firms: peFirms.split('\n').map(line => line.trim()).filter(Boolean),
        }),
      });
      const result = await response.json();
      if (response.ok) {
        showAlert('success', result.message || 'Settings saved successfully!');
        setInitialSettings({ gemini_api_key: geminiApiKey, pe_firms: peFirms });
      } else {
        showAlert('error', result.error || 'Failed to save settings.');
      }
    } catch (error) {
      showAlert('error', `Network error: ${error.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <div style={{textAlign: 'center'}}><CircularProgress /></div>;
  }

  return (
    <Box>
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold', color: '#1a237e' }}>
            Settings
        </Typography>
        <Card>
            <CardContent sx={{ p: 4 }}>
                <form onSubmit={handleSubmit}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                        <TextField
                            label="Gemini API Key"
                            type="password"
                            variant="outlined"
                            fullWidth
                            value={geminiApiKey}
                            onChange={(e) => setGeminiApiKey(e.target.value)}
                            helperText="Your API key is stored locally and used for all analyses."
                        />
                        <TextField
                            label="Known Private Equity Firms"
                            multiline
                            rows={15}
                            variant="outlined"
                            fullWidth
                            value={peFirms}
                            onChange={(e) => setPeFirms(e.target.value)}
                            helperText="Enter one firm name per line. This list helps with initial identification."
                        />
                        <Button
                            type="submit"
                            variant="contained"
                            disabled={!hasChanges || isSaving}
                            size="large"
                            sx={{ py: 1.5, fontWeight: 'bold' }}
                            startIcon={isSaving ? <CircularProgress size={20} color="inherit" /> : <i className="ph ph-floppy-disk text-xl"></i>}
                        >
                            Save Changes
                        </Button>
                    </Box>
                </form>
            </CardContent>
        </Card>
    </Box>
  );
}

export default SettingsSection;
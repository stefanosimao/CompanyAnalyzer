import React, { useState, useEffect } from 'react';
import { Button, Card, CardContent, Typography, Box, CircularProgress, List, ListItem, ListItemText, Divider } from '@mui/material';

function PEInsightsSection({ peFirmName, reportId, showAlert, navigateTo }) {
  const [peFirmData, setPeFirmData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!peFirmName || !reportId) {
      showAlert('error', 'Missing PE firm or report ID.');
      navigateTo('history');
      return;
    }
    const fetchPEInsights = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`/report/${reportId}`);
        const fullReportData = await response.json();
        if (response.ok) {
          const insights = fullReportData.pe_firms_insights;
          if (insights && insights[peFirmName]) {
            setPeFirmData(insights[peFirmName]);
          } else {
            showAlert('error', `PE firm "${peFirmName}" not found in report.`);
            navigateTo('reportDetail', reportId);
          }
        } else {
          showAlert('error', fullReportData.error || 'Failed to load report.');
          navigateTo('history');
        }
      } catch (error) {
        showAlert('error', `Network error: ${error.message}`);
        navigateTo('history');
      } finally {
        setIsLoading(false);
      }
    };
    fetchPEInsights();
  }, [peFirmName, reportId, showAlert, navigateTo]);

  if (isLoading) {
    return <div style={{textAlign: 'center'}}><CircularProgress /></div>;
  }
  if (!peFirmData) {
    return <Typography color="error">Data could not be loaded for {peFirmName}.</Typography>;
  }

  return (
    <Box>
      <Button onClick={() => navigateTo('reportDetail', reportId)} sx={{ mb: 2 }}>
        &larr; Back to Report
      </Button>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold', color: '#1a237e' }}>
        PE Firm Insights: {peFirmData.name}
      </Typography>

      <Card sx={{ mb: 4 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h6" gutterBottom>Profile Summary</Typography>
          <Typography variant="body1" color="text.secondary">
            {peFirmData.profile_summary || 'No profile summary available.'}
          </Typography>
        </CardContent>
      </Card>
      
      <Card>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h6" gutterBottom>Portfolio Companies</Typography>
          {peFirmData.portfolio_companies?.length > 0 ? (
            <List>
              {peFirmData.portfolio_companies.map((company, index) => (
                <React.Fragment key={index}>
                  <ListItem>
                    <ListItemText
                      primary={company.name}
                      secondary={`Headquarters: ${company.headquarters || 'N/A'} | Industry: ${company.industry || 'N/A'}`}
                    />
                  </ListItem>
                  {index < peFirmData.portfolio_companies.length - 1 && <Divider component="li" />}
                </React.Fragment>
              ))}
            </List>
          ) : (
            <Typography>No recent portfolio companies found.</Typography>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}

export default PEInsightsSection;
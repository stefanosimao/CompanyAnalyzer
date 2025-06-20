import React, { useState } from 'react';
import { Button, Card, CardContent, Typography, Box, CircularProgress, Paper } from '@mui/material';

function UploadSection({ showAlert, navigateTo }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0]);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!selectedFile) {
      showAlert('error', 'Please select an Excel file to upload.');
      return;
    }
    setIsUploading(true);
    showAlert('info', 'Uploading file and starting analysis...');

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch('/upload', { method: 'POST', body: formData });
      const result = await response.json();
      if (response.ok) {
        showAlert('success', result.message || 'File uploaded and analysis started!');
        navigateTo('history'); 
      } else {
        showAlert('error', result.error || 'An error occurred during upload.');
      }
    } catch (error) {
      showAlert('error', `Network error: ${error.message}`);
    } finally {
      setIsUploading(false);
      setSelectedFile(null);
      if(document.getElementById('excel-file')) {
        document.getElementById('excel-file').value = '';
      }
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold', color: '#1a237e' }}>
        New Company Analysis
      </Typography>
      <Card>
        <CardContent sx={{ p: 4 }}>
          <form onSubmit={handleSubmit}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <Typography variant="h6">1. Select Excel File</Typography>
              <Typography variant="body2" color="text.secondary">
                Choose an Excel file (.xlsx or .xls) containing a single column with the header 'Company Name'.
              </Typography>
              <Paper
                variant="outlined"
                sx={{
                  p: 2,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  borderStyle: 'dashed',
                  borderColor: isUploading ? 'grey.400' : 'grey.500',
                }}
              >
                <Typography noWrap color={selectedFile ? 'text.primary' : 'text.secondary'}>
                  {selectedFile ? selectedFile.name : 'No file chosen...'}
                </Typography>
                <Button
                  component="label"
                  variant="outlined"
                  disabled={isUploading}
                >
                  Browse
                  <input
                    type="file"
                    id="excel-file"
                    hidden
                    accept=".xlsx,.xls"
                    onChange={handleFileChange}
                  />
                </Button>
              </Paper>
               <Typography variant="h6">2. Start Analysis</Typography>
              <Button
                type="submit"
                variant="contained"
                disabled={!selectedFile || isUploading}
                size="large"
                sx={{ py: 1.5, fontWeight: 'bold' }}
                startIcon={isUploading ? <CircularProgress size={20} color="inherit" /> : <i className="ph ph-paper-plane-tilt text-xl"></i>}
              >
                {isUploading ? 'Analysis in Progress...' : 'Start Analysis'}
              </Button>
            </Box>
          </form>
        </CardContent>
      </Card>
    </Box>
  );
}

export default UploadSection;
import React, { useState, useEffect } from 'react';

// This component displays detailed insights for a specific Private Equity firm,
// including its profile and a list of its portfolio companies.
function PEInsightsSection({ peFirmName, reportId, showAlert, navigateTo }) {
  // State to hold the specific PE firm's data from the report
  const [peFirmData, setPeFirmData] = useState(null);
  // State for loading indicator
  const [isLoading, setIsLoading] = useState(true);

  // useEffect Hook to fetch the full report and then extract the specific PE firm's data
  useEffect(() => {
    // Ensure we have a PE firm name and report ID to fetch data
    if (!peFirmName || !reportId) {
      showAlert('error', 'Missing PE firm name or report ID to load insights.');
      navigateTo('history'); // Go back if essential data is missing
      return;
    }

    const fetchPEInsights = async () => {
      setIsLoading(true);
      setPeFirmData(null); // Clear previous data

      try {
        // Fetch the entire report (which contains pe_firms_insights)
        const response = await fetch(`/report/${reportId}`);
        const fullReportData = await response.json();

        if (response.ok && fullReportData) {
          // Find the specific PE firm's data within the fetched report
          const insights = fullReportData.pe_firms_insights;
          if (insights && insights[peFirmName]) {
            setPeFirmData(insights[peFirmName]);
            showAlert('success', `Loaded insights for ${peFirmName}.`);
          } else {
            showAlert('error', `PE firm "${peFirmName}" not found in this report's insights.`);
            navigateTo('reportDetail', reportId); // Go back to report if PE firm not found
          }
        } else {
          showAlert('error', fullReportData.error || 'Failed to load report for PE insights.');
          navigateTo('history'); // Go back to history if report loading fails
        }
      } catch (error) {
        console.error(`Error fetching PE insights for ${peFirmName}:`, error);
        showAlert('error', `Network error while loading PE insights: ${error.message}`);
        navigateTo('history');
      } finally {
        setIsLoading(false);
      }
    };

    fetchPEInsights();
  }, [peFirmName, reportId, showAlert, navigateTo]); // Re-run if PE firm name or report ID changes

  // Function to navigate back to the main report detail view
  const handleBackToReport = () => {
    navigateTo('reportDetail', reportId);
  };

  // --- JSX Rendering ---

  if (isLoading) {
    return (
      <section id="pe-insights-section" className="main-content-section">
        <div className="text-center py-8 text-gray-500">
          <i className="ph ph-spinner animate-spin text-4xl"></i>
          <p className="mt-2">Loading PE firm insights for {peFirmName}...</p>
        </div>
      </section>
    );
  }

  if (!peFirmData) {
    return (
      <section id="pe-insights-section" className="main-content-section">
        <p className="text-red-500 text-center py-8">No data found for {peFirmName} or an error occurred.</p>
        <button
            onClick={handleBackToReport}
            className="mt-4 text-blue-600 hover:text-blue-800 flex items-center justify-center mx-auto"
        >
            <i className="ph ph-arrow-left mr-2"></i> Back to Report
        </button>
      </section>
    );
  }

  return (
    <section id="pe-insights-section" className="main-content-section animate-fade-in">
      <button className="mb-4 text-blue-600 hover:text-blue-800 flex items-center" onClick={handleBackToReport}>
        <i className="ph ph-arrow-left mr-2"></i> Back to Report
      </button>
      <h2 className="text-3xl font-semibold text-gray-800 mb-6 border-b pb-3">
        PE Firm Insights: <span className="text-purple-700">{peFirmData.name}</span>
      </h2>
      <div className="bg-white p-6 rounded-lg shadow-md mb-8">
        {/* Profile Summary */}
        <h3 className="text-xl font-semibold text-gray-700 mb-4">Profile Summary</h3>
        <p className="text-gray-700 mb-6">{peFirmData.profile_summary || 'No profile summary available.'}</p>

        {/* Portfolio Companies */}
        <h3 className="text-xl font-semibold text-gray-700 mb-4">Portfolio Companies</h3>
        {peFirmData.portfolio_companies && Array.isArray(peFirmData.portfolio_companies) && peFirmData.portfolio_companies.length > 0 ? (
          <div className="space-y-3">
            {peFirmData.portfolio_companies.map((company, index) => (
              <div key={index} className="bg-purple-50 p-3 rounded-lg shadow-sm border border-purple-100">
                <p className="font-semibold text-purple-800">{company.name}</p>
                <p className="text-sm text-gray-700">
                  <span className="font-medium">Headquarters:</span> {company.headquarters || 'N/A'}
                </p>
                <p className="text-sm text-gray-700">
                  <span className="font-medium">Industry:</span> {company.industry || 'N/A'}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No recent portfolio companies found for {peFirmData.name}.</p>
        )}
        {peFirmData.error && (
            <div className="mt-4 pt-4 border-t border-gray-200 text-red-600 text-sm">
                <p><span className="font-bold">Research Error:</span> {peFirmData.error}</p>
            </div>
        )}
      </div>
    </section>
  );
}

export default PEInsightsSection;


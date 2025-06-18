import React, { useState, useEffect, useRef } from 'react';
import { Chart, registerables } from 'chart.js'; // Import Chart.js essentials
import { format, parseISO } from 'date-fns'; // For date formatting

// Register all Chart.js components (like bar, pie, etc.)
Chart.register(...registerables);

// This component displays the detailed view of a single analysis report.
function ReportDetailSection({ reportId, showAlert, navigateTo }) {
  // State for the full report data
  const [reportData, setReportData] = useState(null);
  // State for loading indicator
  const [isLoading, setIsLoading] = useState(true);
  // State for search term within company data
  const [searchTerm, setSearchTerm] = useState('');
  // State for companies filtered by search term
  const [filteredCompanies, setFilteredCompanies] = useState([]);

  // Refs for Chart.js canvases to manage their instances
  const ownershipChartRef = useRef(null);
  const nationChartRef = useRef(null);
  const peOwnerChartRef = useRef(null);

  // Store chart instances so we can destroy them before re-rendering
  const charts = useRef({});

  // --- Utility Functions for Data Processing ---

  // Calculates summary statistics from the raw company data
  const calculateSummary = (companies) => {
    if (!companies || companies.length === 0) {
      return {
        total: 0,
        peOwned: 0,
        public: 0,
        private: 0,
        flaggedPE: 0,
        ownershipDistribution: {},
        nations: {},
        peOwners: {},
      };
    }

    const total = companies.length;
    let peOwned = 0;
    let publicCount = 0;
    let privateCount = 0;
    let flaggedPE = 0;

    const ownershipDistribution = {}; // For pie chart: Public, Private, Unknown
    const nations = {}; // For bar chart: Companies per nation
    const peOwners = {}; // For bar chart: Companies per PE owner

    companies.forEach(company => {
      // Count Public/Private/Unknown
      if (company.public_private === 'Public') {
        publicCount++;
        ownershipDistribution['Public'] = (ownershipDistribution['Public'] || 0) + 1;
      } else if (company.public_private === 'Private') {
        privateCount++;
        ownershipDistribution['Private'] = (ownershipDistribution['Private'] || 0) + 1;
      } else {
        ownershipDistribution['Unknown'] = (ownershipDistribution['Unknown'] || 0) + 1;
      }

      // Count PE Owned
      if (company.is_pe_owned) {
        peOwned++;
      }
      if (company.flagged_as_pe_account) {
        flaggedPE++;
      }

      // Count Companies per Nation
      if (company.nation && company.nation !== 'Unknown' && company.nation !== 'N/A') {
        // Handle multiple nations if present (e.g., "USA, Germany")
        const nationList = company.nation.split(',').map(n => n.trim()).filter(n => n);
        nationList.forEach(nation => {
            nations[nation] = (nations[nation] || 0) + 1;
        });
      }

      // Count Companies per PE Owner (if multiple, distribute count)
      if (company.pe_owner_names && company.pe_owner_names.length > 0) {
        company.pe_owner_names.forEach(owner => {
          peOwners[owner] = (peOwners[owner] || 0) + 1;
        });
      }
    });

    return {
      total,
      peOwned,
      public: publicCount,
      private: privateCount,
      flaggedPE,
      ownershipDistribution,
      nations,
      peOwners,
    };
  };

  // Renders a Chart.js chart given canvas ID, type, and data
  const renderChart = (canvasRef, chartId, type, labels, data, backgroundColor) => {
    // Destroy previous chart instance if it exists
    if (charts.current[chartId]) {
      charts.current[chartId].destroy();
    }
    
    const ctx = canvasRef.current.getContext('2d');
    charts.current[chartId] = new Chart(ctx, {
      type: type,
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: backgroundColor,
          borderColor: '#fff',
          borderWidth: 1,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false, // Allow charts to resize dynamically
        plugins: {
          legend: {
            position: 'top',
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                let label = context.label || '';
                if (label) {
                  label += ': ';
                }
                if (context.parsed.pie !== undefined) { // For pie chart percentages
                    const totalSum = context.dataset.data.reduce((sum, val) => sum + val, 0);
                    const percentage = totalSum > 0 ? ((context.parsed.pie / totalSum) * 100).toFixed(1) : 0;
                    label += `${context.parsed.pie} (${percentage}%)`;
                } else { // For bar chart
                    label += context.parsed.y;
                }
                return label;
              }
            }
          }
        },
        scales: type === 'bar' ? {
          y: {
            beginAtZero: true,
            ticks: {
              precision: 0 // Ensure whole numbers for counts
            }
          }
        } : {}
      },
    });
  };

  // --- useEffect Hooks for Data Fetching and Chart Rendering ---

  // Effect to fetch report data when component mounts or reportId changes
  useEffect(() => {
    if (!reportId) {
      setIsLoading(false);
      setReportData(null);
      setFilteredCompanies([]);
      return;
    }

    const fetchReport = async () => {
      setIsLoading(true);
      setReportData(null); // Clear previous data
      setFilteredCompanies([]);
      setSearchTerm(''); // Clear search term on new report load

      try {
        const response = await fetch(`/report/${reportId}`);
        const data = await response.json();

        if (response.ok) {
          setReportData(data);
          setFilteredCompanies(data.data || []); // Initialize filtered companies with all data
          showAlert('success', `Report "${data.report_name}" loaded successfully.`);
        } else {
          showAlert('error', data.error || 'Failed to load report.');
          navigateTo('history'); // Go back to history if report not found
        }
      } catch (error) {
        console.error('Error fetching report:', error);
        showAlert('error', `Network error while loading report: ${error.message}`);
        navigateTo('history');
      } finally {
        setIsLoading(false);
      }
    };

    fetchReport();
  }, [reportId, showAlert, navigateTo]); // Re-run if reportId changes

  // Effect to render charts whenever reportData or its content changes
  useEffect(() => {
    if (reportData && reportData.data && reportData.data.length > 0) {
      const summary = calculateSummary(reportData.data);

      // 1. Ownership Distribution Chart (Pie)
      const ownershipLabels = Object.keys(summary.ownershipDistribution);
      const ownershipData = Object.values(summary.ownershipDistribution);
      const ownershipColors = [
        'rgba(59, 130, 246, 0.8)', // blue-500 for Public
        'rgba(234, 88, 12, 0.8)',  // orange-600 for Private
        'rgba(107, 114, 128, 0.8)' // gray-500 for Unknown
      ];
      renderChart(ownershipChartRef, 'ownershipChart', 'pie', ownershipLabels, ownershipData, ownershipColors);

      // 2. Companies per Nation Chart (Bar)
      // Sort nations by count descending for better visualization
      const sortedNations = Object.entries(summary.nations).sort(([, a], [, b]) => b - a);
      const nationLabels = sortedNations.map(([nation]) => nation);
      const nationData = sortedNations.map(([, count]) => count);
      const nationColors = nationLabels.map(() => 'rgba(22, 163, 74, 0.8)'); // green-600
      renderChart(nationChartRef, 'nationChart', 'bar', nationLabels, nationData, nationColors);

      // 3. Companies per PE Owner Chart (Bar)
      const sortedPEOwners = Object.entries(summary.peOwners).sort(([, a], [, b]) => b - a);
      const peOwnerLabels = sortedPEOwners.map(([owner]) => owner);
      const peOwnerData = sortedPEOwners.map(([, count]) => count);
      const peOwnerColors = peOwnerLabels.map(() => 'rgba(124, 58, 237, 0.8)'); // purple-600
      renderChart(peOwnerChartRef, 'peOwnerChart', 'bar', peOwnerLabels, peOwnerData, peOwnerColors);
    } else {
        // Destroy charts if no data or reportData is cleared
        Object.values(charts.current).forEach(chart => chart.destroy());
        charts.current = {}; // Clear the ref
    }
    // Cleanup function: destroy charts when component unmounts or data changes
    return () => {
        Object.values(charts.current).forEach(chart => chart.destroy());
        charts.current = {};
    };
  }, [reportData]); // Re-run when reportData changes

  // Effect to filter companies based on search term
  useEffect(() => {
    if (reportData && reportData.data) {
      const lowerCaseSearchTerm = searchTerm.toLowerCase();
      const filtered = reportData.data.filter(company =>
        company.company_name.toLowerCase().includes(lowerCaseSearchTerm)
      );
      setFilteredCompanies(filtered);
    }
  }, [searchTerm, reportData]); // Re-run when search term or report data changes

  // --- JSX Rendering ---

  if (isLoading) {
    return (
      <section id="report-detail-section" className="main-content-section">
        <div className="text-center py-8 text-gray-500">
          <i className="ph ph-spinner animate-spin text-4xl"></i>
          <p className="mt-2">Loading report details...</p>
        </div>
      </section>
    );
  }

  if (!reportData) {
    return (
      <section id="report-detail-section" className="main-content-section">
        <p className="text-red-500 text-center py-8">No report data found or an error occurred.</p>
        <button
            onClick={() => navigateTo('history')}
            className="mt-4 text-blue-600 hover:text-blue-800 flex items-center justify-center mx-auto"
        >
            <i className="ph ph-arrow-left mr-2"></i> Back to History
        </button>
      </section>
    );
  }

  const summary = calculateSummary(reportData.data);
  const totalCompanies = summary.total;

  return (
    <section id="report-detail-section" className="main-content-section animate-fade-in">
      <button id="back-to-history" className="mb-4 text-blue-600 hover:text-blue-800 flex items-center" onClick={() => navigateTo('history')}>
        <i className="ph ph-arrow-left mr-2"></i> Back to History
      </button>
      <h2 className="text-3xl font-semibold text-gray-800 mb-6 border-b pb-3">
        Report: <span id="report-title">{reportData.report_name}</span>
      </h2>
      <div className="bg-white p-6 rounded-lg shadow-md mb-8">
        <h3 className="text-xl font-semibold text-gray-700 mb-4">Summary Statistics</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
          <div className="bg-blue-50 p-4 rounded-lg shadow-sm">
            <p className="text-sm text-gray-600">Total Companies</p>
            <p id="summary-total-companies" className="text-2xl font-bold text-blue-800">{summary.total}</p>
          </div>
          <div className="bg-blue-50 p-4 rounded-lg shadow-sm">
            <p className="text-sm text-gray-600">Analysis Duration</p>
            <p id="summary-duration" className="text-2xl font-bold text-blue-800">
                {formatDuration(reportData.analysis_duration_seconds)}
            </p>
          </div>
          <div className="bg-blue-50 p-4 rounded-lg shadow-sm">
            <p class="text-sm text-gray-600">PE Owned Companies</p>
            <p id="summary-pe-owned" className="text-2xl font-bold text-blue-800">
                {summary.peOwned} ({totalCompanies > 0 ? ((summary.peOwned / totalCompanies) * 100).toFixed(1) : 0}%)
            </p>
          </div>
          <div className="bg-blue-50 p-4 rounded-lg shadow-sm">
            <p class="text-sm text-gray-600">Public Companies</p>
            <p id="summary-public" className="text-2xl font-bold text-blue-800">
                {summary.public} ({totalCompanies > 0 ? ((summary.public / totalCompanies) * 100).toFixed(1) : 0}%)
            </p>
          </div>
          <div className="bg-blue-50 p-4 rounded-lg shadow-sm">
            <p class="text-sm text-gray-600">Private Companies</p>
            <p id="summary-private" className="text-2xl font-bold text-blue-800">
                {summary.private} ({totalCompanies > 0 ? ((summary.private / totalCompanies) * 100).toFixed(1) : 0}%)
            </p>
          </div>
          <div className="bg-blue-50 p-4 rounded-lg shadow-sm">
            <p className="text-sm text-gray-600">Companies flagged as PE Account</p>
            <p id="summary-flagged-pe" className="text-2xl font-bold text-blue-800">
                {summary.flaggedPE} ({totalCompanies > 0 ? ((summary.flaggedPE / totalCompanies) * 100).toFixed(1) : 0}%)
            </p>
          </div>
        </div>

        {/* Ownership Distribution Chart */}
        <h3 className="text-xl font-semibold text-gray-700 mb-4 mt-6">Ownership Distribution</h3>
        <div id="ownership-chart-container" className="w-full h-64 bg-gray-100 rounded-lg p-4">
          <canvas ref={ownershipChartRef} id="ownershipChart"></canvas>
        </div>

        {/* Companies per Nation Chart */}
        <h3 className="text-xl font-semibold text-gray-700 mb-4 mt-6">Companies per Nation</h3>
        <div id="nation-chart-container" className="w-full h-72 bg-gray-100 rounded-lg p-4">
          <canvas ref={nationChartRef} id="nationChart"></canvas>
        </div>

        {/* Companies per PE Owner Chart */}
        <h3 className="text-xl font-semibold text-gray-700 mb-4 mt-6">Companies per PE Owner</h3>
        <div id="pe-owner-chart-container" className="w-full h-72 bg-gray-100 rounded-lg p-4">
          <canvas ref={peOwnerChartRef} id="peOwnerChart"></canvas>
        </div>

        {/* PE Firms Insights Overview */}
        {Object.keys(reportData.pe_firms_insights || {}).length > 0 && (
            <>
                <h3 className="text-xl font-semibold text-gray-700 mb-4 mt-6">Private Equity Firm Insights</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {Object.values(reportData.pe_firms_insights).map(peFirm => (
                        <div 
                            key={peFirm.name} 
                            className="bg-white p-4 rounded-lg shadow border border-purple-200 cursor-pointer hover:bg-purple-50 transition-colors duration-200"
                            onClick={() => navigateTo('peInsights', reportId, peFirm.name)}
                        >
                            <h4 className="text-lg font-semibold text-purple-700 mb-1">{peFirm.name}</h4>
                            <p className="text-sm text-gray-600 truncate">{peFirm.profile_summary || 'No profile summary available.'}</p>
                            {peFirm.portfolio_companies && Array.isArray(peFirm.portfolio_companies) && peFirm.portfolio_companies.length > 0 && (
                                <p className="text-xs text-gray-500 mt-1">
                                    Includes {peFirm.portfolio_companies.length} portfolio companies found. Click for details.
                                </p>
                            )}
                        </div>
                    ))}
                </div>
            </>
        )}

        {/* Detailed Company Data Search and List */}
        <h3 className="text-xl font-semibold text-gray-700 mb-4 mt-6">Detailed Company Data</h3>
        <div className="mb-4 flex flex-col sm:flex-row items-center space-y-2 sm:space-y-0 sm:space-x-4">
          <input
            type="text"
            id="company-search-input"
            placeholder="Search for a company name..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <button
            id="clear-search-button"
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors duration-200"
            onClick={() => setSearchTerm('')}
          >
            Clear Search
          </button>
        </div>
        <div id="company-results" className="space-y-4">
          {filteredCompanies.length === 0 ? (
            <p className="text-gray-500 text-center py-4">No companies match your search or no data available.</p>
          ) : (
            filteredCompanies.map((company) => (
              <div key={company.company_name} className="company-card bg-gray-50 p-4 rounded-lg shadow-sm border border-gray-200">
                <h4 className="text-xl font-semibold text-blue-700 mb-2 company-name">{company.company_name}</h4>
                <p><span className="font-medium">Public/Private:</span> <span className="public-private text-gray-700">{company.public_private}</span></p>
                <p><span className="font-medium">Ownership Structure:</span> <span className="ownership-structure text-gray-700">{company.ownership_structure}</span></p>
                <p><span className="font-medium">PE Owned:</span> <span className="is-pe-owned text-gray-700">{company.is_pe_owned ? 'Yes' : 'No'}</span></p>
                {company.pe_owner_names && company.pe_owner_names.length > 0 && (
                  <p className="pe-owner-names-row"><span className="font-medium">PE Owners:</span> <span className="pe-owner-names text-gray-700">{company.pe_owner_names.join(', ')}</span></p>
                )}
                <p><span className="font-medium">Is itself a PE Firm:</span> <span className="is-itself-pe text-gray-700">{company.is_itself_pe ? 'Yes' : 'No'}</span></p>
                <p><span className="font-medium">Revenue:</span> <span className="revenue text-gray-700">{company.revenue}</span> {company.revenue_year !== 'N/A' && <span className="text-sm text-gray-500 revenue-year">({company.revenue_year})</span>}</p>
                <p><span className="font-medium">Employees:</span> <span className="employees text-gray-700">{company.employees}</span> {company.employees_year !== 'N/A' && <span className="text-sm text-gray-500 employees-year">({company.employees_year})</span>}</p>
                <p><span className="font-medium">Nation:</span> <span className="nation text-gray-700">{company.nation}</span></p>
                {company.flagged_as_pe_account && (
                  <p className="flagged-as-pe-account-row text-red-600 font-bold mt-2"><i className="ph ph-flag mr-1"></i>Flagged as PE Account (&gt;=50% PE Ownership)</p>
                )}
                
                {/* Source Snippets */}
                {company.source_snippets && company.source_snippets.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <h5 className="text-md font-semibold text-gray-700 mb-2">Source Snippets:</h5>
                    <div className="source-snippets text-sm text-gray-600 space-y-1">
                      {company.source_snippets.map((snippet, idx) => (
                        <p key={idx}>
                          "{snippet.snippet}" - <a href={snippet.url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">{snippet.source_title || snippet.url}</a>
                        </p>
                      ))}
                    </div>
                  </div>
                )}
                {company.error && (
                  <div className="mt-4 pt-4 border-t border-gray-200 text-red-600 text-sm">
                      <p><span className="font-bold">Analysis Error:</span> {company.error}</p>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}

export default ReportDetailSection;


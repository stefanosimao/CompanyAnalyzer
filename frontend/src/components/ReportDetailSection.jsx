import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, Treemap } from 'recharts';
import { format, parseISO } from 'date-fns';

// --- Reusable Components for Modern UI ---
const Card = ({ children, className = '' }) => (
  <div className={`bg-card text-card-foreground p-6 rounded-xl border border-border shadow-sm ${className}`}>
    {children}
  </div>
);

const StatCard = ({ title, value, icon }) => (
  <Card>
    <div className="flex items-center justify-between">
      <p className="text-sm font-medium text-muted-foreground">{title}</p>
      <i className={`ph ph-${icon} text-lg text-muted-foreground`}></i>
    </div>
    <p className="text-2xl font-bold mt-1">{value}</p>
  </Card>
);


// --- Main Report Detail Component ---
function ReportDetailSection({ reportId, showAlert, navigateTo }) {
  const [reportData, setReportData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredCompanies, setFilteredCompanies] = useState([]);
  
  // New state for sorting
  const [sortConfig, setSortConfig] = useState({ key: 'company_name', direction: 'ascending' });

  const formatDuration = (seconds) => {
    if (typeof seconds !== 'number' || isNaN(seconds)) return 'N/A';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    return minutes > 0 ? `${minutes}m ${remainingSeconds}s` : `${remainingSeconds}s`;
  };

  // Fetch report data
  useEffect(() => {
    if (!reportId) return;
    const fetchReport = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`/report/${reportId}`);
        const data = await response.json();
        if (response.ok) {
          setReportData(data);
          showAlert('success', `Report "${data.report_name}" loaded.`);
        } else {
          showAlert('error', data.error || 'Failed to load report.');
          navigateTo('history');
        }
      } catch (error) {
        showAlert('error', `Network error: ${error.message}`);
        navigateTo('history');
      } finally {
        setIsLoading(false);
      }
    };
    fetchReport();
  }, [reportId, showAlert, navigateTo]);

  // Handle sorting and filtering
  useEffect(() => {
    if (!reportData?.data) return;

    let sortableItems = [...reportData.data];
    
    // Filtering logic
    if (searchTerm) {
        sortableItems = sortableItems.filter(company =>
            company.company_name.toLowerCase().includes(searchTerm.toLowerCase())
        );
    }
    
    // Sorting logic
    sortableItems.sort((a, b) => {
      if (a[sortConfig.key] < b[sortConfig.key]) {
        return sort_config.direction === 'ascending' ? -1 : 1;
      }
      if (a[sortConfig.key] > b[sortConfig.key]) {
        return sortConfig.direction === 'ascending' ? 1 : -1;
      }
      return 0;
    });

    setFilteredCompanies(sortableItems);
  }, [reportData, searchTerm, sortConfig]);

  const requestSort = (key) => {
    let direction = 'ascending';
    if (sortConfig.key === key && sortConfig.direction === 'ascending') {
      direction = 'descending';
    }
    setSortConfig({ key, direction });
  };

  // --- Data preparation for charts ---
  const summary = React.useMemo(() => {
    if (!reportData?.data) return {};
    const companies = reportData.data;
    const total = companies.length;
    const peOwned = companies.filter(c => c.is_pe_owned).length;

    const ownershipDistribution = companies.reduce((acc, c) => {
        const type = c.public_private || 'Unknown';
        acc[type] = (acc[type] || 0) + 1;
        return acc;
    }, {});
    
    const nations = companies.reduce((acc, c) => {
        if (c.nation && c.nation !== 'Unknown') {
            acc[c.nation] = (acc[c.nation] || 0) + 1;
        }
        return acc;
    }, {});

    const peOwners = companies.reduce((acc, c) => {
        if (c.is_pe_owned && c.pe_owner_names) {
            c.pe_owner_names.forEach(owner => {
                acc[owner] = (acc[owner] || 0) + 1;
            });
        }
        return acc;
    }, {});

    return {
      total,
      peOwned,
      public: ownershipDistribution['Public'] || 0,
      private: ownershipDistribution['Private'] || 0,
      ownershipData: Object.entries(ownershipDistribution).map(([name, value]) => ({ name, value })),
      nationData: Object.entries(nations).map(([name, value]) => ({ name, value })).sort((a,b) => b.value - a.value),
      peOwnerData: Object.entries(peOwners).map(([name, value]) => ({ name, size: value })) // For Treemap
    };
  }, [reportData]);

  // --- Loading and Error States ---
  if (isLoading) return <div className="text-center py-8"><i className="ph ph-spinner animate-spin text-4xl text-primary"></i></div>;
  if (!reportData) return <p className="text-red-500">Report not found.</p>;

  // --- Render ---
  return (
    <section className="space-y-8 animate-fade-in">
      <button className="text-primary font-semibold flex items-center" onClick={() => navigateTo('history')}>
        <i className="ph ph-arrow-left mr-2"></i> Back to History
      </button>

      <div>
        <h2 className="text-3xl font-bold text-foreground">{reportData.report_name}</h2>
        <p className="text-muted-foreground">Analysis completed on {format(parseISO(reportData.analysis_end_time), 'MMM dd, yyyy')}</p>
      </div>

      {/* Summary Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
        <StatCard title="Total Companies" value={summary.total} icon="buildings" />
        <StatCard title="Analysis Duration" value={formatDuration(reportData.analysis_duration_seconds)} icon="timer" />
        <StatCard title="PE Owned" value={`${summary.peOwned} (${summary.total > 0 ? ((summary.peOwned / summary.total) * 100).toFixed(1) : 0}%)`} icon="briefcase" />
      </div>

      {/* Charts section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card>
            <h3 className="font-semibold mb-4">Ownership Distribution</h3>
            <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                    <Pie data={summary.ownershipData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} fill="#8884d8" label>
                        <Cell key="cell-0" fill="#3b82f6" />
                        <Cell key="cell-1" fill="#f97316" />
                        <Cell key="cell-2" fill="#6b7280" />
                    </Pie>
                    <Tooltip />
                    <Legend />
                </PieChart>
            </ResponsiveContainer>
        </Card>
        <Card>
            <h3 className="font-semibold mb-4">Companies by Nation</h3>
            <ResponsiveContainer width="100%" height={300}>
                <BarChart data={summary.nationData} layout="vertical" margin={{ top: 5, right: 20, left: 60, bottom: 5 }}>
                    <XAxis type="number" />
                    <YAxis type="category" dataKey="name" width={80} />
                    <Tooltip cursor={{fill: 'rgba(238, 242, 255, 0.5)'}} />
                    <Bar dataKey="value" fill="#16a34a" />
                </BarChart>
            </ResponsiveContainer>
        </Card>
      </div>
      
      {/* Treemap for PE owners */}
      {summary.peOwnerData && summary.peOwnerData.length > 0 && (
        <Card>
            <h3 className="font-semibold mb-4">PE Firm Ownership</h3>
            <ResponsiveContainer width="100%" height={400}>
                <Treemap
                    data={summary.peOwnerData}
                    dataKey="size"
                    ratio={4 / 3}
                    stroke="#fff"
                    fill="#8884d8"
                />
            </ResponsiveContainer>
        </Card>
      )}

      {/* Detailed Company List */}
      <Card>
        <h3 className="text-xl font-semibold mb-4">Detailed Analysis</h3>
        <input
            type="text"
            placeholder="Search companies in this report..."
            className="w-full mb-4 px-4 py-2 border rounded-lg"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
        />
        <div className="space-y-4">
          {filteredCompanies.map((company) => (
            <div key={company.company_name} className="p-4 border rounded-lg bg-secondary/50">
                <h4 className="text-lg font-bold text-primary">{company.company_name}</h4>
                <div className="grid grid-cols-2 gap-x-4 gap-y-2 mt-2 text-sm">
                    <p><span className="font-semibold">Status:</span> {company.public_private}</p>
                    <p><span className="font-semibold">PE Owned:</span> {company.is_pe_owned ? 'Yes' : 'No'}</p>
                    <p><span className="font-semibold">Nation:</span> {company.nation}</p>
                    {company.pe_owner_names.length > 0 && (
                        <p className="col-span-2"><span className="font-semibold">PE Owners:</span> {company.pe_owner_names.join(', ')}</p>
                    )}
                    <p className="col-span-2 mt-2"><span className="font-semibold">Ownership Details:</span> {company.ownership_structure}</p>
                </div>
            </div>
          ))}
        </div>
      </Card>

    </section>
  );
}

export default ReportDetailSection;
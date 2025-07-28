import React, { useState, useEffect, useMemo } from "react";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { format, parseISO } from "date-fns";

// --- Reusable Component ---
const Card = ({ children, className = "" }) => (
  <div
    className={`bg-white text-gray-800 p-6 rounded-lg border border-gray-200 shadow-sm ${className}`}
  >
    {children}
  </div>
);

// Custom Tooltip for Recharts
const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    return (
      <div className="p-2 bg-white/80 backdrop-blur-sm border border-gray-200 rounded-lg shadow-lg">
        <p className="label font-bold text-gray-700">{`${payload[0].name} : ${payload[0].value}`}</p>
      </div>
    );
  }
  return null;
};

// Colors for our charts
const COLORS = [
  "#2563eb",
  "#16a34a",
  "#ea580c",
  "#64748b",
  "#9333ea",
  "#fde047",
];

// --- Main Report Detail Component ---
function ReportDetailSection({ reportId, showAlert, navigateTo }) {
  const [reportData, setReportData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [activeFilters, setActiveFilters] = useState([]);

  const formatDuration = (seconds) => {
    if (typeof seconds !== "number" || isNaN(seconds)) return "N/A";
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    if (minutes > 0) return `~${minutes}m ${remainingSeconds}s`;
    return `${remainingSeconds}s`;
  };

  useEffect(() => {
    if (!reportId) return;
    const fetchReport = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`/report/${reportId}`);
        const data = await response.json();
        if (response.ok) {
          setReportData(data);
        } else {
          showAlert("error", data.error || "Failed to load report.");
          navigateTo("history");
        }
      } catch (error) {
        showAlert("error", `Network error: ${error.message}`);
        navigateTo("history");
      } finally {
        setIsLoading(false);
      }
    };
    fetchReport();
  }, [reportId, showAlert, navigateTo]);

  const { summary, filteredCompanies } = useMemo(() => {
    if (!reportData?.data) return { summary: {}, filteredCompanies: [] };

    const companies = reportData.data;
    const categoryDistribution = companies.reduce((acc, c) => {
      const type = c.ownership_category || "Unknown";
      acc[type] = (acc[type] || 0) + 1;
      return acc;
    }, {});

    const peRelatedCount =
      (categoryDistribution["PE-Owned"] || 0) +
      (categoryDistribution["Public (PE-Backed)"] || 0);

    const nations = companies.reduce((acc, c) => {
      if (c.nation && c.nation !== "Unknown")
        acc[c.nation] = (acc[c.nation] || 0) + 1;
      return acc;
    }, {});

    const summaryData = {
      total: companies.length,
      peRelatedCount,
      categoryData: Object.entries(categoryDistribution).map(
        ([name, value]) => ({ name, value })
      ),
      nationData: Object.entries(nations)
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 10),
    };

    let processedCompanies = [...reportData.data];
    if (searchTerm) {
      processedCompanies = processedCompanies.filter((c) =>
        c.company_name.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }
    activeFilters.forEach((filter) => {
      processedCompanies = processedCompanies.filter(
        (c) => c[filter.type] === filter.value
      );
    });

    return { summary: summaryData, filteredCompanies: processedCompanies };
  }, [reportData, searchTerm, activeFilters]);

  const addFilter = (type, value) => {
    if (!activeFilters.some((f) => f.type === type && f.value === value)) {
      setActiveFilters([...activeFilters, { type, value }]);
    }
  };

  const removeFilter = (filterToRemove) => {
    setActiveFilters(
      activeFilters.filter(
        (f) =>
          !(f.type === filterToRemove.type && f.value === filterToRemove.value)
      )
    );
  };

  if (isLoading)
    return (
      <div className="text-center py-8">
        <i className="ph-fill ph-spinner-gap animate-spin text-4xl text-blue-600"></i>
      </div>
    );
  if (!reportData) return <p className="text-red-600">Report not found.</p>;

  return (
    <section className="space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <button
          className="text-blue-600 font-semibold flex items-center mb-4"
          onClick={() => navigateTo("history")}
        >
          <i className="ph-fill ph-arrow-left mr-2"></i> Back to History
        </button>
        <h2 className="text-3xl font-bold text-gray-800">
          {reportData.report_name}
        </h2>
        <p className="text-gray-500">
          Analysis completed on{" "}
          {reportData.analysis_end_time
            ? format(parseISO(reportData.analysis_end_time), "MMM dd, yyyy")
            : "N/A"}
        </p>
      </div>

      {/* Executive Summary Section (Unchanged, as requested) */}
      <Card>
        <h3 className="text-xl font-semibold mb-4 text-gray-800">
          Executive Summary
        </h3>
        <div className="flex flex-col md:flex-row md:items-center gap-8">
          <div className="text-center">
            <p className="text-sm text-gray-500">
              Companies with Private Equities Involvement:{" "}
              <strong className="font-semibold text-blue-600">
                {summary.peRelatedCount}
              </strong>
            </p>
          </div>
          <div className="border-l border-gray-200 pl-8">
            <p className="text-gray-700 mb-2">
              This report analyzed{" "}
              <strong className="font-semibold">{summary.total}</strong>{" "}
              companies and found that{" "}
              <strong className="font-semibold">
                {((summary.peRelatedCount / summary.total) * 100).toFixed(0)}%
              </strong>{" "}
              have direct private equity ownership or backing.
            </p>
            <p className="text-sm text-gray-500">
              The full analysis was completed in{" "}
              <strong className="font-semibold">
                {formatDuration(reportData.analysis_duration_seconds)}
              </strong>
              .
            </p>
          </div>
        </div>
      </Card>

      {/* ** FIX **: Updated grid layout for charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        <Card className="lg:col-span-2">
          <h3 className="font-semibold mb-4 text-gray-800">
            Ownership Category
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={summary.categoryData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={5}
                onClick={(data) => addFilter("ownership_category", data.name)}
              >
                {summary.categoryData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[index % COLORS.length]}
                    className="cursor-pointer"
                  />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </Card>
        <Card className="lg:col-span-3">
          <h3 className="font-semibold mb-4 text-gray-800">Top 10 Nations</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={summary.nationData}
              margin={{ top: 5, right: 20, left: 20, bottom: 5 }}
            >
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip
                content={<CustomTooltip />}
                cursor={{ fill: "rgba(238, 242, 255, 0.5)" }}
              />
              <Bar
                dataKey="count"
                fill="#16a34a"
                radius={[4, 4, 0, 0]}
                onClick={(data) => addFilter("nation", data.name)}
                className="cursor-pointer"
              />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Detailed Company List */}
      <Card>
        <div className="flex flex-col md:flex-row gap-4 mb-4">
          <input
            type="text"
            placeholder="Search companies in this report..."
            className="w-full px-4 py-2 border rounded-lg bg-gray-50"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          {activeFilters.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              {activeFilters.map((filter) => (
                <div
                  key={`${filter.type}-${filter.value}`}
                  className="flex items-center gap-1 bg-gray-200 px-2 py-1 rounded"
                >
                  <span className="text-sm">{filter.value}</span>
                  <button
                    onClick={() => removeFilter(filter)}
                    className="text-gray-500 hover:text-red-500"
                  >
                    <i className="ph-fill ph-x-circle"></i>
                  </button>
                </div>
              ))}
              <button
                onClick={() => setActiveFilters([])}
                className="text-sm text-blue-600 hover:underline"
              >
                Reset Filters
              </button>
            </div>
          )}
        </div>
        <div className="space-y-4">
          {filteredCompanies.length > 0 ? (
            filteredCompanies.map((company) => (
              <div
                key={company.company_name}
                className="p-4 border rounded-lg bg-gray-50/50"
              >
                <h4 className="text-lg font-bold text-blue-600">
                  {company.company_name}
                </h4>
                <div className="mt-2 text-sm space-y-2">
                  <p>
                    <strong className="font-semibold text-gray-700">
                      Category:
                    </strong>{" "}
                    <span
                      className={
                        company.is_pe_owned ? "text-green-600 font-bold" : ""
                      }
                    >
                      {company.ownership_category || "N/A"}
                    </span>
                  </p>
                  <p>
                    <strong className="font-semibold text-gray-700">
                      Status:
                    </strong>{" "}
                    {company.public_private}
                  </p>
                  <p>
                    <strong className="font-semibold text-gray-700">
                      Nation:
                    </strong>{" "}
                    {company.nation}
                  </p>
                  {company.pe_owner_names &&
                    company.pe_owner_names.length > 0 && (
                      <p>
                        <strong className="font-semibold text-gray-700">
                          PE Owners:
                        </strong>{" "}
                        {company.pe_owner_names.join(", ")}
                      </p>
                    )}
                  <p className="pt-2 border-t border-gray-200/50">
                    <strong className="font-semibold text-gray-700">
                      Ownership Summary:
                    </strong>{" "}
                    <span className="text-gray-500">
                      {company.ownership_structure}
                    </span>
                  </p>
                </div>
              </div>
            ))
          ) : (
            <p className="text-center text-gray-500 py-4">
              No companies match the current filters.
            </p>
          )}
        </div>
      </Card>
    </section>
  );
}

export default ReportDetailSection;

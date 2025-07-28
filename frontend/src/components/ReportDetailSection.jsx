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
  Treemap,
} from "recharts";
import { format, parseISO } from "date-fns";

// --- Reusable Components for Modern UI ---
const Card = ({ children, className = "" }) => (
  <div
    className={`bg-card text-card-foreground p-6 rounded-lg border border-border shadow-sm ${className}`}
  >
    {children}
  </div>
);

const StatCard = ({ title, value, icon }) => (
  <Card className="flex flex-col justify-between">
    <div>
      <div className="flex items-center justify-between text-muted-foreground">
        <p className="text-sm font-medium">{title}</p>
        <i className={`ph-fill ph-${icon} text-lg`}></i>
      </div>
      <p className="text-3xl font-bold mt-1 text-foreground">{value}</p>
    </div>
  </Card>
);

// Custom Tooltip for Recharts
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="p-2 bg-background/80 backdrop-blur-sm border border-border rounded-lg shadow-lg">
        <p className="label font-bold">{`${label} : ${payload[0].value}`}</p>
      </div>
    );
  }
  return null;
};

// --- Main Report Detail Component ---
function ReportDetailSection({ reportId, showAlert, navigateTo }) {
  const [reportData, setReportData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortConfig, setSortConfig] = useState({
    key: "company_name",
    direction: "ascending",
  });

  const formatDuration = (seconds) => {
    if (typeof seconds !== "number" || isNaN(seconds)) return "N/A";
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    return minutes > 0
      ? `${minutes}m ${remainingSeconds}s`
      : `${remainingSeconds}s`;
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

  const { summary, filteredAndSortedCompanies } = useMemo(() => {
    if (!reportData?.data)
      return { summary: {}, filteredAndSortedCompanies: [] };

    // --- Data Calculation ---
    const companies = reportData.data;
    const total = companies.length;
    const peOwned = companies.filter((c) => c.is_pe_owned).length;
    const ownershipDistribution = companies.reduce((acc, c) => {
      const type = c.public_private || "Unknown";
      acc[type] = (acc[type] || 0) + 1;
      return acc;
    }, {});
    const nations = companies.reduce((acc, c) => {
      if (c.nation && c.nation !== "Unknown")
        acc[c.nation] = (acc[c.nation] || 0) + 1;
      return acc;
    }, {});
    const peOwners = companies.reduce((acc, c) => {
      if (c.is_pe_owned && c.pe_owner_names)
        c.pe_owner_names.forEach(
          (owner) => (acc[owner] = (acc[owner] || 0) + 1)
        );
      return acc;
    }, {});

    const summaryData = {
      total,
      peOwned,
      ownershipData: Object.entries(ownershipDistribution).map(
        ([name, value]) => ({ name, value })
      ),
      nationData: Object.entries(nations)
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 10),
      peOwnerData: Object.entries(peOwners).map(([name, size]) => ({
        name,
        size,
      })),
    };

    // --- Filtering and Sorting ---
    let processedCompanies = [...reportData.data];
    if (searchTerm) {
      processedCompanies = processedCompanies.filter((c) =>
        c.company_name.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }
    processedCompanies.sort((a, b) => {
      if (a[sortConfig.key] < b[sortConfig.key])
        return sortConfig.direction === "ascending" ? -1 : 1;
      if (a[sortConfig.key] > b[sortConfig.key])
        return sortConfig.direction === "ascending" ? 1 : -1;
      return 0;
    });

    return {
      summary: summaryData,
      filteredAndSortedCompanies: processedCompanies,
    };
  }, [reportData, searchTerm, sortConfig]);

  if (isLoading)
    return (
      <div className="text-center py-8">
        <i className="ph-fill ph-spinner-gap animate-spin text-4xl text-primary"></i>
      </div>
    );
  if (!reportData) return <p className="text-destructive">Report not found.</p>;

  return (
    <section className="space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <button
          className="text-primary font-semibold flex items-center mb-4"
          onClick={() => navigateTo("history")}
        >
          <i className="ph-fill ph-arrow-left mr-2"></i> Back to History
        </button>
        <h2 className="text-3xl font-bold text-foreground">
          {reportData.report_name}
        </h2>
        <p className="text-muted-foreground">
          Analysis completed on{" "}
          {format(parseISO(reportData.analysis_end_time), "MMM dd, yyyy")}
        </p>
      </div>

      {/* Summary Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <StatCard
          title="Total Companies"
          value={summary.total}
          icon="buildings"
        />
        <StatCard
          title="PE Owned"
          value={summary.peOwned}
          icon="briefcase-metal"
        />
        <StatCard
          title="Analysis Duration"
          value={formatDuration(reportData.analysis_duration_seconds)}
          icon="timer"
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <Card className="lg:col-span-2">
          <h3 className="font-semibold mb-4 text-foreground">
            Ownership Distribution
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={summary.ownershipData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={5}
                labelLine={false}
                label={({ name, percent }) =>
                  `${name} ${(percent * 100).toFixed(0)}%`
                }
              >
                <Cell key="cell-0" fill="#2563eb" />
                <Cell key="cell-1" fill="#ea580c" />
                <Cell key="cell-2" fill="#64748b" />
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </Card>
        <Card className="lg:col-span-3">
          <h3 className="font-semibold mb-4 text-foreground">Top 10 Nations</h3>
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
              <Bar dataKey="count" fill="#16a34a" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Treemap for PE owners */}
      {summary.peOwnerData?.length > 0 && (
        <Card>
          <h3 className="font-semibold mb-4 text-foreground">
            PE Firm Portfolio Size
          </h3>
          <ResponsiveContainer width="100%" height={400}>
            <Treemap
              data={summary.peOwnerData}
              dataKey="size"
              ratio={4 / 3}
              stroke="#fff"
              fill="#4f46e5"
              content={
                <CustomizedContent
                  colors={["#6366f1", "#818cf8", "#a5b4fc", "#c7d2fe"]}
                />
              }
            />
          </ResponsiveContainer>
        </Card>
      )}

      {/* Detailed Company List */}
      <Card>
        <h3 className="text-xl font-semibold mb-4 text-foreground">
          Detailed Company Data
        </h3>
        <input
          type="text"
          placeholder="Search companies in this report..."
          className="w-full mb-4 px-4 py-2 border rounded-lg bg-background"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        <div className="space-y-4">
          {filteredAndSortedCompanies.map((company) => (
            <div
              key={company.company_name}
              className="p-4 border rounded-lg bg-secondary/50"
            >
              <h4 className="text-lg font-bold text-primary">
                {company.company_name}
              </h4>
              <div className="mt-2 text-sm space-y-2">
                <p>
                  <strong className="font-semibold text-foreground">
                    Status:
                  </strong>{" "}
                  {company.public_private}
                </p>
                <p>
                  <strong className="font-semibold text-foreground">
                    PE Owned:
                  </strong>{" "}
                  <span
                    className={
                      company.is_pe_owned ? "text-green-600 font-bold" : ""
                    }
                  >
                    {company.is_pe_owned ? "Yes" : "No"}
                  </span>
                </p>
                <p>
                  <strong className="font-semibold text-foreground">
                    Nation:
                  </strong>{" "}
                  {company.nation}
                </p>
                {company.pe_owner_names.length > 0 && (
                  <p>
                    <strong className="font-semibold text-foreground">
                      PE Owners:
                    </strong>{" "}
                    {company.pe_owner_names.join(", ")}
                  </p>
                )}
                <p className="pt-2 border-t border-border/50">
                  <strong className="font-semibold text-foreground">
                    Ownership Details:
                  </strong>{" "}
                  <span className="text-muted-foreground">
                    {company.ownership_structure}
                  </span>
                </p>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </section>
  );
}

// Helper for the Treemap colors
const CustomizedContent = ({
  root,
  depth,
  x,
  y,
  width,
  height,
  index,
  colors,
  name,
}) => {
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        style={{
          fill: colors[
            Math.floor((index / root.children.length) * colors.length)
          ],
          stroke: "#fff",
          strokeWidth: 2,
        }}
      />
      <text
        x={x + width / 2}
        y={y + height / 2 + 7}
        textAnchor="middle"
        fill="#fff"
        fontSize={14}
      >
        {name}
      </text>
    </g>
  );
};

export default ReportDetailSection;

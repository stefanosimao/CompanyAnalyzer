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
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  CircularProgress,
  TextField,
  Chip,
  Button,
} from "@mui/material";

// --- Reusable Card Component --- (Using MUI Card now for consistency)

// --- Corrected Custom Tooltip for Recharts ---
const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0];
    // For Pie charts, the name is `data.name`. For Bar charts, it's inside `data.payload.name`.
    const name = data.payload.name || data.name;
    const value = data.value;

    return (
      <Card sx={{ bgcolor: "rgba(255, 255, 255, 0.9)", p: 1 }}>
        <Typography
          variant="body2"
          sx={{ fontWeight: "bold" }}
        >{`${name}: ${value}`}</Typography>
      </Card>
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
      <Box sx={{ textAlign: "center", py: 4 }}>
        <CircularProgress />
      </Box>
    );
  if (!reportData)
    return <Typography color="error">Report not found.</Typography>;

  return (
    <Box
      sx={{ width: "100%", display: "flex", flexDirection: "column", gap: 3 }}
    >
      {/* Header */}
      <Box>
        <Button
          onClick={() => navigateTo("history")}
          startIcon={<i className="ph ph-arrow-left"></i>}
          sx={{ mb: 2 }}
        >
          Back to History
        </Button>
        <Typography variant="h4" gutterBottom sx={{ fontWeight: "bold" }}>
          {reportData.report_name}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Analysis completed on{" "}
          {reportData.analysis_end_time
            ? format(parseISO(reportData.analysis_end_time), "MMM dd, yyyy")
            : "N/A"}
        </Typography>
      </Box>

      {/* Executive Summary */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Executive Summary
          </Typography>
          <Typography variant="body1">
            This report analyzed <strong>{summary.total}</strong> companies and
            found that{" "}
            <strong>
              {summary.peRelatedCount} (
              {((summary.peRelatedCount / summary.total) * 100).toFixed(0)}%)
            </strong>{" "}
            have direct private equity ownership or backing.
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            The full analysis was completed in{" "}
            <strong>
              {formatDuration(reportData.analysis_duration_seconds)}
            </strong>
            .
          </Typography>
        </CardContent>
      </Card>

      {/* Charts Section */}
      <Box
        sx={{
          display: "flex",
          gap: 3,
          flexDirection: { xs: "column", md: "row" },
        }}
      >
        <Box sx={{ flex: { md: 5, lg: 4 } }}>
          {" "}
          {/* Corresponds to md={5} lg={4} */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Ownership Category
              </Typography>
              <ResponsiveContainer width="100%" height={500}>
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
                    onClick={(data) =>
                      addFilter("ownership_category", data.payload.name)
                    }
                  >
                    {summary.categoryData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={COLORS[index % COLORS.length]}
                        style={{ cursor: "pointer" }}
                      />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Box>
        <Box sx={{ flex: { md: 7, lg: 8 } }}>
          {" "}
          {/* Corresponds to md={7} lg={8} */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Top 10 Nations
              </Typography>
              <ResponsiveContainer width="100%" height={500}>
                <BarChart
                  data={summary.nationData}
                  margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
                >
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis />
                  <Tooltip
                    content={<CustomTooltip />}
                    cursor={{ fill: "rgba(238, 242, 255, 0.7)" }}
                  />
                  <Bar
                    dataKey="count"
                    fill="#16a34a"
                    radius={[4, 4, 0, 0]}
                    onClick={(data) => addFilter("nation", data.name)}
                    style={{ cursor: "pointer" }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Box>
      </Box>

      {/* Detailed Company List */}
      <Card>
        <CardContent>
          {/* Search and Filters */}
          <Box sx={{ display: "flex", gap: 2, mb: 2, flexWrap: "wrap" }}>
            <TextField
              label="Search companies..."
              variant="outlined"
              size="small"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              sx={{ flexGrow: 1 }}
            />
            {activeFilters.length > 0 && (
              <Button onClick={() => setActiveFilters([])} size="small">
                Reset Filters
              </Button>
            )}
          </Box>
          {activeFilters.length > 0 && (
            <Box sx={{ display: "flex", gap: 1, mb: 2, flexWrap: "wrap" }}>
              {activeFilters.map((filter) => (
                <Chip
                  key={`${filter.type}-${filter.value}`}
                  label={filter.value}
                  onDelete={() => removeFilter(filter)}
                  size="small"
                />
              ))}
            </Box>
          )}

          {/* Company List */}
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {filteredCompanies.length > 0 ? (
              filteredCompanies.map((company) => (
                <Box
                  key={company.company_name}
                  sx={{
                    p: 2,
                    border: "1px solid #e0e0e0",
                    borderRadius: 2,
                    bgcolor: "#f9f9f9",
                  }}
                >
                  <Typography variant="h6" color="primary">
                    {company.company_name}
                  </Typography>
                  <Grid container spacing={2} sx={{ mt: 1 }}>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="body2">
                        <strong>Category:</strong>{" "}
                        {company.ownership_category || "N/A"}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="body2">
                        <strong>Status:</strong> {company.public_private}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="body2">
                        <strong>Nation:</strong> {company.nation}
                      </Typography>
                    </Grid>
                    {company.pe_owner_names &&
                      company.pe_owner_names.length > 0 && (
                        <Grid item xs={12}>
                          <Typography variant="body2">
                            <strong>PE Owners:</strong>{" "}
                            {company.pe_owner_names.join(", ")}
                          </Typography>
                        </Grid>
                      )}
                    <Grid item xs={12}>
                      <Typography variant="body2" color="text.secondary">
                        <strong>Summary:</strong> {company.ownership_structure}
                      </Typography>
                    </Grid>
                  </Grid>
                </Box>
              ))
            ) : (
              <Typography
                sx={{ textAlign: "center", color: "text.secondary", py: 4 }}
              >
                No companies match the current filters.
              </Typography>
            )}
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}

export default ReportDetailSection;

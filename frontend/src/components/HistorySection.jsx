import React, { useState, useEffect } from "react";
import {
  Button,
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Chip,
  IconButton,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import { format, parseISO } from "date-fns";

function HistorySection({ showAlert, navigateTo }) {
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [reportToDelete, setReportToDelete] = useState(null);

  useEffect(() => {
    const fetchHistory = async () => {
      setIsLoading(true);
      try {
        const response = await fetch("/history");
        const data = await response.json();
        setHistory(response.ok ? data : []);
        if (!response.ok)
          showAlert("error", data.error || "Failed to load history.");
      } catch (error) {
        showAlert("error", `Network error: ${error.message}`);
      } finally {
        setIsLoading(false);
      }
    };
    fetchHistory();
    const interval = setInterval(fetchHistory, 10000); // Poll every 10 seconds
    return () => clearInterval(interval);
  }, [showAlert]);

  const formatDuration = (seconds) => {
    if (typeof seconds !== "number" || isNaN(seconds)) return "N/A";
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    return minutes > 0
      ? `${minutes}m ${remainingSeconds}s`
      : `${remainingSeconds}s`;
  };

  const openDeleteDialog = (report) => {
    setReportToDelete(report);
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setReportToDelete(null);
    setDialogOpen(false);
  };

  const handleConfirmDelete = async () => {
    if (!reportToDelete) return;

    try {
      const response = await fetch(`/report/${reportToDelete.id}`, {
        method: "DELETE",
      });
      const result = await response.json();

      if (response.ok) {
        showAlert("success", result.message || "Report deleted!");
        // Optimistically update the UI by removing the deleted report from state
        setHistory((prevHistory) =>
          prevHistory.filter((item) => item.id !== reportToDelete.id)
        );
      } else {
        showAlert("error", result.error || "Failed to delete report.");
      }
    } catch (error) {
      showAlert("error", `Network error: ${error.message}`);
    } finally {
      handleCloseDialog();
    }
  };

  return (
    <Box>
      <Typography
        variant="h4"
        gutterBottom
        sx={{ fontWeight: "bold", color: "#1a237e" }}
      >
        Analysis History
      </Typography>
      {isLoading && history.length === 0 ? (
        <div style={{ textAlign: "center" }}>
          <CircularProgress />
        </div>
      ) : history.length === 0 ? (
        <Typography>
          No analysis history found. Upload a file to start!
        </Typography>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {history.map((entry) => (
            <Card
              key={entry.id}
              onClick={() =>
                entry.status === "Completed" &&
                navigateTo("reportDetail", entry.id)
              }
              sx={{
                cursor: entry.status === "Completed" ? "pointer" : "default",
                "&:hover": { boxShadow: entry.status === "Completed" ? 6 : 1 },
              }}
            >
              <CardContent>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <Typography
                    variant="h6"
                    component="h3"
                    sx={{ fontWeight: "600" }}
                  >
                    {entry.name}
                  </Typography>
                  <Chip
                    label={entry.status}
                    color={entry.status === "Completed" ? "success" : "warning"}
                    size="small"
                    sx={{ fontWeight: "bold" }}
                  />
                  <IconButton
                    aria-label="delete report"
                    color="error"
                    onClick={(e) => {
                      e.stopPropagation(); // Prevent card click event
                      openDeleteDialog(entry);
                    }}
                  >
                    <DeleteIcon />
                  </IconButton>
                </Box>
                <Box
                  sx={{
                    mt: 1,
                    display: "flex",
                    gap: 4,
                    color: "text.secondary",
                  }}
                >
                  <Typography variant="body2">
                    {entry.date
                      ? format(parseISO(entry.date), "MMM dd, yyyy HH:mm")
                      : "N/A"}
                  </Typography>
                  <Typography variant="body2">
                    Companies: {entry.num_companies || "N/A"}
                  </Typography>
                  {entry.status === "Completed" && (
                    <Typography variant="body2">
                      Duration:{" "}
                      {formatDuration(entry.analysis_duration_seconds)}
                    </Typography>
                  )}
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}
    </Box>
  );
}

export default HistorySection;

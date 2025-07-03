import React, { useEffect, useState, useCallback } from 'react';
import {
    Typography, Container, Paper, Box, CircularProgress, Alert, Button,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, IconButton,
    Grid, TextField, Select, MenuItem, FormControl, InputLabel, SelectChangeEvent,
    Dialog, DialogTitle, DialogContent, DialogActions, List, ListItem, ListItemText, Divider, Tooltip
} from '@mui/material';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import RefreshIcon from '@mui/icons-material/Refresh';
import AssessmentIcon from '@mui/icons-material/Assessment';
import AccessTimeIcon from '@mui/icons-material/AccessTime'; // For PENDING status icon
import Plot from 'react-plotly.js';
import { DatePicker, LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterMoment } from '@mui/x-date-pickers/AdapterMoment';
import moment, { Moment } from 'moment';

import * as reportService from '../services/reportService';
import { useAuth } from '../contexts/AuthContext';
import { useNotifier } from '../contexts/NotificationContext'; // Import useNotifier

interface ActiveReportTask {
    reportId: number;
    taskId: string;
    reportName?: string | null;
}

const POLLING_INTERVAL = 5000; // 5 seconds

const ReportsPage: React.FC = () => {
    const [reports, setReports] = useState<reportService.Report[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(false); // For main list loading
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    const { isAuthenticated } = useAuth();

    const [summaryReportType, setSummaryReportType] = useState<"DAILY" | "WEEKLY">("DAILY");

    const initialBacktestParams: reportService.GenerateBacktestReportRequest = {
        report_name: '',
        strategy_name: 'zscore_mean_reversion_v1',
        tickers: [],
        start_date: moment().subtract(1, 'year').format('YYYY-MM-DD'),
        end_date: moment().format('YYYY-MM-DD'),
        initial_capital: 100000,
        z_score_window: 20,
        entry_z_threshold: 2.0,
        exit_z_threshold: 0.5,
    };
    const [backtestParams, setBacktestParams] = useState<reportService.GenerateBacktestReportRequest>(initialBacktestParams);
    const [backtestTickersInput, setBacktestTickersInput] = useState<string>('');

    const [selectedReportDetails, setSelectedReportDetails] = useState<reportService.Report | null>(null);
    const [openReportDetailsDialog, setOpenReportDetailsDialog] = useState(false);
    const [equityCurveData, setEquityCurveData] = useState<any[]>([]);
    const [equityCurveLayout, setEquityCurveLayout] = useState<any>({});

    // State to keep track of report generation tasks currently being processed by Celery.
    // Each object contains the report's database ID and the Celery task ID for polling.
    const [activeReportTasks, setActiveReportTasks] = useState<ActiveReportTask[]>([]);
    // Flag to manage the polling interval's active state to prevent multiple intervals.
    const [isPolling, setIsPolling] = useState<boolean>(false);
    const notifier = useNotifier();

    const updateReportInList = (updatedReportData: Partial<reportService.Report> & { id: number | string }) => {
        setReports(prevReports =>
            prevReports.map(report =>
                String(report.id) === String(updatedReportData.id) ? { ...report, ...updatedReportData } : report
            )
        );
    };

    const fetchReports = useCallback(async () => {
        if (!isAuthenticated) return;
        setIsLoading(true);
        setError(null);
        try {
            const fetchedReports = await reportService.getGeneratedReports();
            setReports(fetchedReports);
        } catch (err: any) {
            setError(err.message || 'Failed to fetch reports list.');
            setReports([]);
        } finally {
            setIsLoading(false);
        }
    }, [isAuthenticated]);

    useEffect(() => {
        fetchReports();
    }, [fetchReports]);


    // Effect hook to manage the polling interval for active report tasks.
    // It starts an interval when there are active tasks and isPolling is false.
    // The interval polls the status of each active task and updates the UI accordingly.
    // It stops polling for tasks that reach a terminal state (SUCCESS/FAILURE) and
    // then refreshes the entire reports list to get final, authoritative metadata.
    // The interval is cleared when no tasks are active or when the component unmounts.
    useEffect(() => {
        let intervalId: NodeJS.Timeout | null = null;

        if (activeReportTasks.length > 0 && !isPolling) {
            setIsPolling(true);

            intervalId = setInterval(async () => {
                console.log("Polling for active report tasks:", activeReportTasks.map(t => t.taskId)); // For debugging
                let stillActiveTasks: ActiveReportTask[] = [];
                let refreshListNeeded = false;

                for (const activeTask of activeReportTasks) {
                    try {
                        const taskStatus = await reportService.getReportTaskStatus(activeTask.taskId);

                        const currentStatus = taskStatus.status?.toUpperCase(); // Normalize status

                        if (currentStatus === "SUCCESS" || currentStatus === "FAILURE") {
                            console.log(`Task ${activeTask.taskId} (Report ID ${activeTask.reportId}) completed with status: ${currentStatus}`);
                            refreshListNeeded = true;
                            notifier.showNotification(
                                `Report '${activeTask.reportName || activeTask.reportId}' ${currentStatus === "SUCCESS" ? "completed successfully" : "failed"}. ${currentStatus === "FAILURE" && taskStatus.result ? String(taskStatus.result).substring(0,100) : '' }`,
                                currentStatus === "SUCCESS" ? "success" : "error"
                            );
                        } else if (currentStatus === "PENDING" || currentStatus === "STARTED" || currentStatus === "PROCESSING") {
                            stillActiveTasks.push(activeTask);
                            updateReportInList({ id: activeTask.reportId, status: currentStatus });
                        } else {
                            console.warn(`Task ${activeTask.taskId} has unknown status: ${taskStatus.status}`);
                            stillActiveTasks.push(activeTask); // Keep polling for unknown status for now
                        }
                    } catch (err: any) {
                        console.error(`Error polling status for task ${activeTask.taskId}:`, err);
                        stillActiveTasks.push(activeTask); // Keep polling even if one poll fails
                        // setError(`Polling failed for task ${activeTask.taskId}.`); // This might be too noisy
                    }
                }

                setActiveReportTasks(stillActiveTasks);

                if (refreshListNeeded) {
                    console.log("A task finished or failed, refreshing the reports list.");
                    fetchReports();
                }

                if (stillActiveTasks.length === 0) {
                     setIsPolling(false); // Stop polling if no tasks left
                }

            }, POLLING_INTERVAL);

        } else if (activeReportTasks.length === 0 && isPolling) {
            setIsPolling(false); // Explicitly stop if tasks are cleared
        }

        // Cleanup function for when the component unmounts or dependencies change
        return () => {
            if (intervalId) {
                clearInterval(intervalId);
            }
            // Do not set isPolling to false here if intervalId was null and activeReportTasks > 0
            // as it might prevent the interval from starting on next render.
            // The conditions at the start of the effect handle setting isPolling.
            if (activeReportTasks.length === 0) {
                setIsPolling(false);
            }
        };
    }, [activeReportTasks, fetchReports, isPolling]);


    const handleRequestSummaryReport = async () => {
        setError(null); setSuccessMessage(null); setIsLoading(true);
        try {
            const reportName = `Summary ${summaryReportType} (${new Date().toLocaleDateString()})`;
            const result = await reportService.requestSummaryReportGeneration({ report_type: summaryReportType });
            // setSuccessMessage(result.message || `Requested ${summaryReportType.toLowerCase()} summary. Task ID: ${result.task_id}. Monitoring status...`);
            notifier.showNotification(`Summary report (${summaryReportType}) generation started. Task ID: ${result.task_id}`, 'info');

            const newReportEntry: reportService.Report = {
                id: String(result.report_id), // Ensure ID is string if service returns number but state expects string
                report_type: `${summaryReportType.toUpperCase()}_SUMMARY`,
                generated_at: new Date().toISOString(), status: result.status || "PENDING",
                report_name: reportName,
            };
            setReports(prev => [newReportEntry, ...prev.filter(r => String(r.id) !== String(newReportEntry.id))]); // Add or update
            setActiveReportTasks(prev => [...prev.filter(t => t.reportId !== result.report_id), { reportId: result.report_id, taskId: result.task_id, reportName }]);

        } catch (err: any) {
            const errorMsg = err.message || 'Failed to request summary report.';
            setError(errorMsg);
            notifier.showNotification(errorMsg, 'error');
        } finally { setIsLoading(false); }
    };

    const handleBacktestParamsChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement> | SelectChangeEvent<string>) => {
        const { name, value } = event.target;
        const numFields = ['initial_capital', 'z_score_window', 'entry_z_threshold', 'exit_z_threshold'];
        const parsedValue = numFields.includes(name) ? (value === '' ? undefined : parseFloat(value)) : value;
        setBacktestParams(prev => ({ ...prev, [name as string]: parsedValue }));
    };

    const handleBacktestDateChange = (field: 'start_date' | 'end_date') => (date: Moment | null) => {
        setBacktestParams(prev => ({ ...prev, [field]: date ? date.format('YYYY-MM-DD') : initialBacktestParams[field] }));
    };

    const handleBacktestTickersChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        setBacktestTickersInput(event.target.value);
        const tickersArray = event.target.value.split(',').map(t => t.trim().toUpperCase()).filter(t => t);
        setBacktestParams(prev => ({ ...prev, tickers: tickersArray }));
    };

    const handleRequestBacktestReport = async () => {
        setError(null); setSuccessMessage(null);
        if (backtestParams.tickers.length !== 2) { setError("Backtesting requires exactly one pair of two tickers (Y,X)."); return; }
        if (!backtestParams.start_date || !backtestParams.end_date) { setError("Start date and end date are required for backtest."); return; }

        setIsLoading(true);
        try {
            const reportName = backtestParams.report_name ||
                               `Backtest: ${backtestParams.tickers.join('/')} (${backtestParams.strategy_name.substring(0,10)}...) ${new Date().toLocaleDateString()}`;
            const paramsToSubmit = { ...backtestParams, report_name: reportName };

            const result = await reportService.requestBacktestReportGeneration(paramsToSubmit);
            // setSuccessMessage(result.message || `Requested backtest for ${reportName}. Task ID: ${result.task_id}. Monitoring status...`);
            notifier.showNotification(`Backtest report '${reportName}' generation started. Task ID: ${result.task_id}`, 'info');

            const newReportEntry: reportService.Report = {
                id: String(result.report_id), report_type: "BACKTEST",
                generated_at: new Date().toISOString(), status: result.status || "PENDING",
                report_name: reportName, parameters: backtestParams,
            };
            setReports(prev => [newReportEntry, ...prev.filter(r => String(r.id) !== String(newReportEntry.id))]);
            setActiveReportTasks(prev => [...prev.filter(t => t.reportId !== result.report_id), { reportId: result.report_id, taskId: result.task_id, reportName }]);

        } catch (err: any) {
            const errorMsg = err.message || 'Failed to request backtest report.';
            setError(errorMsg);
            notifier.showNotification(errorMsg, 'error');
        } finally { setIsLoading(false); }
    };

    const handleDownload = (report: reportService.Report, format: 'pdf' | 'csv') => {
        let downloadUrl: string | undefined = undefined;
        let fileNameInDb: string | undefined = undefined;

        if (format === 'pdf') {
            downloadUrl = report.download_url_pdf; // Prefer fully formed URL from backend
            fileNameInDb = report.file_path_pdf; // Check if file was generated
        } else if (format === 'csv') {
            downloadUrl = report.download_url_csv;
            fileNameInDb = report.file_path_csv;
        }

        if (report.status !== "COMPLETED") {
            notifier.showNotification(`Report is still '${report.status}'. Please wait for completion.`, 'warning');
            return;
        }

        if (!downloadUrl && fileNameInDb) {
            // If backend doesn't provide full download_url_*, construct it based on convention
            downloadUrl = `/api/v1/reports/${report.id}/download/${format}`;
        }

        if (downloadUrl) {
            notifier.showNotification(`Preparing ${format.toUpperCase()} download for "${report.report_name || report.id}"...`, 'info');
            window.open(downloadUrl, '_blank');
        } else {
            notifier.showNotification(`Download URL for ${format.toUpperCase()} not available for report "${report.report_name || report.id}". File might not have been generated.`, 'error');
        }
    };

    const handleViewReportDetails = (report: reportService.Report) => {
        setSelectedReportDetails(report);
        if (report.report_type === "BACKTEST" && report.summary_data &&
            Array.isArray(report.summary_data.equity_curve_dates) &&
            Array.isArray(report.summary_data.equity_curve_values)) {

            setEquityCurveData([{
                x: report.summary_data.equity_curve_dates.map((d: string) => new Date(d)),
                y: report.summary_data.equity_curve_values,
                type: 'scatter',
                mode: 'lines',
                name: 'Equity Curve (Spread P&L Units)'
            }]);

            setEquityCurveLayout({
                title: `Equity Curve: ${report.report_name || `Report ID ${report.id}`}`,
                xaxis: { title: 'Date', type: 'date', automargin: true },
                yaxis: { title: 'Cumulative P&L (Spread Units)', automargin: true },
                autosize: true,
                height: 400,
                margin: { l: 70, r: 50, b: 80, t: 80, pad: 4 },
            });
        } else {
            setEquityCurveData([]);
            setEquityCurveLayout({});
        }
        setOpenReportDetailsDialog(true);
    };
    const handleCloseReportDetailsDialog = () => setOpenReportDetailsDialog(false);

    if (!isAuthenticated) {
        return (
            <Container>
                <Alert severity="warning" sx={{ mt: 3 }}>Please login to manage and view reports.</Alert>
            </Container>
        );
     }

    return (
        <LocalizationProvider dateAdapter={AdapterMoment}>
        <Container maxWidth="lg">
            <Typography variant="h4" component="h1" gutterBottom sx={{ my: 2 }}>Reports Center</Typography>

            {isLoading && activeReportTasks.length === 0 && <Box sx={{ display: 'flex', justifyContent: 'center', my: 1 }}><CircularProgress size={24} /></Box>}
            {error && <Alert severity="error" sx={{ my: 2, width: '100%' }} onClose={() => setError(null)}>{error}</Alert>}
            {successMessage && <Alert severity="success" sx={{ my: 2, width: '100%' }} onClose={() => setSuccessMessage(null)}>{successMessage}</Alert>}

            <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                    <Paper sx={{ p: 2, mb: 3 }}>
                        <Typography variant="h6" gutterBottom>Request Summary Report</Typography>
                        <FormControl fullWidth margin="normal">
                            <InputLabel id="summary-report-type-label">Report Type</InputLabel>
                            <Select labelId="summary-report-type-label" value={summaryReportType} label="Report Type"
                                onChange={(e) => setSummaryReportType(e.target.value as "DAILY" | "WEEKLY")}>
                                <MenuItem value="DAILY">Daily Performance</MenuItem>
                                <MenuItem value="WEEKLY">Weekly Performance</MenuItem>
                            </Select>
                        </FormControl>
                         <Button variant="contained" startIcon={<PlayArrowIcon />} onClick={handleRequestSummaryReport} disabled={isLoading && activeReportTasks.length > 0} sx={{mt:1}}>Generate Summary</Button>
                    </Paper>
                </Grid>

                <Grid item xs={12} md={6}>
                    <Paper sx={{ p: 2, mb: 3 }}>
                        <Typography variant="h6" gutterBottom>Request Backtest Report</Typography>
                        <TextField name="report_name" label="Report Name (Optional)" value={backtestParams.report_name || ''} onChange={handleBacktestParamsChange} fullWidth margin="normal" />
                        <TextField name="strategy_name" label="Strategy Name" value={backtestParams.strategy_name} onChange={handleBacktestParamsChange} fullWidth margin="normal" />
                        <TextField label="Tickers for Pair (Y,X)" value={backtestTickersInput} onChange={handleBacktestTickersChange} fullWidth margin="normal" helperText="e.g. PETR4.SA,VALE3.SA (comma-separated)" />
                        <Grid container spacing={2} sx={{mb:1}}>
                            <Grid item xs={6}><DatePicker label="Start Date" value={moment(backtestParams.start_date)} onChange={handleBacktestDateChange('start_date')} sx={{width: "100%"}}/></Grid>
                            <Grid item xs={6}><DatePicker label="End Date" value={moment(backtestParams.end_date)} onChange={handleBacktestDateChange('end_date')} sx={{width: "100%"}} /></Grid>
                        </Grid>
                        <TextField name="initial_capital" label="Initial Capital" type="number" value={backtestParams.initial_capital} onChange={handleBacktestParamsChange} fullWidth margin="normal" InputLabelProps={{ shrink: true }}/>
                        <Grid container spacing={2}>
                            <Grid item xs={12} sm={4}><TextField name="z_score_window" label="Z Window" type="number" value={backtestParams.z_score_window} onChange={handleBacktestParamsChange} fullWidth margin="normal" InputLabelProps={{ shrink: true }}/></Grid>
                            <Grid item xs={12} sm={4}><TextField name="entry_z_threshold" label="Entry Z" type="number" value={backtestParams.entry_z_threshold} onChange={handleBacktestParamsChange} fullWidth margin="normal" InputLabelProps={{ shrink: true }}/></Grid>
                            <Grid item xs={12} sm={4}><TextField name="exit_z_threshold" label="Exit Z" type="number" value={backtestParams.exit_z_threshold} onChange={handleBacktestParamsChange} fullWidth margin="normal" InputLabelProps={{ shrink: true }}/></Grid>
                        </Grid>
                        <Button variant="contained" startIcon={<PlayArrowIcon />} onClick={handleRequestBacktestReport} disabled={isLoading && activeReportTasks.length > 0} sx={{mt:2}}>Run Backtest</Button>
                    </Paper>
                </Grid>
            </Grid>

            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', my: 2 }}>
                <Typography variant="h5" gutterBottom>Generated Reports</Typography>
                <Button variant="outlined" startIcon={<RefreshIcon />} onClick={fetchReports} disabled={isLoading && activeReportTasks.length === 0}>Refresh List</Button>
            </Box>
            <TableContainer component={Paper}>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>Name/ID</TableCell><TableCell>Type</TableCell><TableCell>Generated At</TableCell>
                            <TableCell>Status</TableCell><TableCell align="left">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {reports.length === 0 && !isLoading && (
                            <TableRow><TableCell colSpan={5} align="center">No reports found.</TableCell></TableRow>
                        )}
                        {reports.map((report) => (
                            <TableRow key={report.id} hover>
                                <TableCell>{report.report_name || report.id}</TableCell>
                                <TableCell>{report.report_type}</TableCell>
                                <TableCell>{new Date(report.generated_at).toLocaleString()}</TableCell>
                                <TableCell>
                                    {report.status === "PROCESSING" || report.status === "STARTED" ? (
                                        <Box sx={{ display: 'flex', alignItems: 'center' }} title={report.status}>
                                            <CircularProgress size={16} sx={{ mr: 1 }} />
                                            <Typography variant="caption">{report.status}</Typography>
                                        </Box>
                                    ) : report.status === "PENDING" ? (
                                        <Box sx={{ display: 'flex', alignItems: 'center' }} title={report.status}>
                                            <AccessTimeIcon fontSize="inherit" sx={{ mr: 0.5, color: 'text.secondary', width: 16, height: 16 }} />
                                            <Typography variant="caption">{report.status}</Typography>
                                        </Box>
                                    ) : (
                                        report.status || 'N/A'
                                    )}
                                </TableCell>
                                <TableCell align="left">
                                    {report.status === "COMPLETED" && (
                                        <Tooltip title="View Report Details">
                                            <IconButton size="small" onClick={() => handleViewReportDetails(report)} color="primary">
                                                <AssessmentIcon />
                                            </IconButton>
                                        </Tooltip>
                                    )}
                                    {report.status === "COMPLETED" && report.file_path_pdf && (
                                        <Tooltip title="Download PDF">
                                            <IconButton size="small" onClick={() => handleDownload(report, 'pdf')} color="error" sx={{ml:0.5}}>
                                                <FileDownloadIcon /> <Typography variant="caption" sx={{ml:0.25}}>PDF</Typography>
                                            </IconButton>
                                        </Tooltip>
                                    )}
                                    {report.status === "COMPLETED" && report.file_path_csv && (
                                        <Tooltip title="Download CSV">
                                            <IconButton size="small" onClick={() => handleDownload(report, 'csv')} sx={{ml:0.5, color: 'green' }}>
                                                <FileDownloadIcon /> <Typography variant="caption" sx={{ml:0.25}}>CSV</Typography>
                                            </IconButton>
                                        </Tooltip>
                                    )}
                                    {(report.status === "PENDING" || report.status === "PROCESSING" || report.status === "STARTED") && !isLoading && ( // Show spinner if task is active and main list not loading
                                        <CircularProgress size={20} titleAccess={report.status} />
                                    )}
                                    {report.status === "FAILED" && (
                                        <Tooltip title={report.error_message || "Report generation failed"}>
                                            <Typography variant="caption" color="error">Failed</Typography>
                                        </Tooltip>
                                    )}
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            <Dialog open={openReportDetailsDialog} onClose={handleCloseReportDetailsDialog} maxWidth="lg" fullWidth>
                <DialogTitle>Report Details: {selectedReportDetails?.report_name || selectedReportDetails?.id}</DialogTitle>
                <DialogContent>
                    {selectedReportDetails?.summary_data ? (
                        <Box>
                            <Typography variant="h6" gutterBottom>Parameters Used:</Typography>
                            <Paper variant="outlined" sx={{p:1, mb:2, fontSize: '0.8rem', overflowX: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                                <pre>{JSON.stringify(selectedReportDetails.parameters || {}, null, 2)}</pre>
                            </Paper>

                            <Typography variant="h6" gutterBottom>Key Metrics:</Typography>
                            <Grid container spacing={1}>
                                {Object.entries(selectedReportDetails.summary_data)
                                    .filter(([key]) => !['equity_curve_dates', 'equity_curve_values', 'trades_log_sample', 'parameters'].includes(key))
                                    .map(([key, value]) => (
                                    <Grid item xs={12} sm={6} md={4} key={key}>
                                        <ListItem dense disableGutters sx={{pb:0}}>
                                            <ListItemText
                                                primaryTypographyProps={{variant: 'subtitle2', component: 'strong', textTransform: 'capitalize'}}
                                                secondaryTypographyProps={{variant: 'body2'}}
                                                primary={`${key.replace(/_/g, ' ')}:`}
                                                secondary={typeof value === 'number' ? value.toFixed(2) : String(value)} />
                                        </ListItem>
                                    </Grid>
                                ))}
                            </Grid>
                            <Divider sx={{my:2}}/>
                            {equityCurveData.length > 0 && equityCurveData[0].x && equityCurveData[0].x.length > 0 && (
                                <>
                                <Typography variant="h6" sx={{mt:2, mb:1}}>Equity Curve (Spread P&L Units)</Typography>
                                <Plot data={equityCurveData} layout={equityCurveLayout} style={{ width: '100%', height: '400px' }} useResizeHandler config={{responsive: true}}/>
                                </>
                            )}
                            {selectedReportDetails.summary_data.trades_log_sample && selectedReportDetails.summary_data.trades_log_sample.length > 0 && (
                                <>
                                <Typography variant="h6" sx={{mt:2, mb:1}}>Sample Trades Log:</Typography>
                                <Paper variant="outlined" sx={{p:1, fontSize: '0.75rem', maxHeight: 200, overflowY: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all'}}>
                                    <pre>{JSON.stringify(selectedReportDetails.summary_data.trades_log_sample, null, 2)}</pre>
                                </Paper>
                                </>
                            )}
                        </Box>
                    ) : (
                        <Typography>No summary data available or report is still processing.</Typography>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleCloseReportDetailsDialog}>Close</Button>
                </DialogActions>
            </Dialog>

        </Container>
        </LocalizationProvider>
    );
};
export default ReportsPage;
```

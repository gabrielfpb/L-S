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
import AssessmentIcon from '@mui/icons-material/Assessment'; // For View Results
import Plot from 'react-plotly.js';
import { DatePicker, LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterMoment } from '@mui/x-date-pickers/AdapterMoment';
import moment, { Moment } from 'moment';

import * as reportService from '../services/reportService';
import { useAuth } from '../contexts/AuthContext';

const ReportsPage: React.FC = () => {
    const [reports, setReports] = useState<reportService.Report[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    const { isAuthenticated } = useAuth();

    const [summaryReportType, setSummaryReportType] = useState<"DAILY" | "WEEKLY">("DAILY");

    // State for Backtest Report Request Form
    const initialBacktestParams: reportService.GenerateBacktestReportRequest = {
        report_name: '', // Optional user-defined name for the report instance
        strategy_name: 'zscore_mean_reversion_v1', // Default strategy identifier for the backend
        tickers: [], // Expects an array of two strings, e.g., ["PETR4.SA", "VALE3.SA"]
        start_date: moment().subtract(1, 'year').format('YYYY-MM-DD'), // Default: one year ago
        end_date: moment().format('YYYY-MM-DD'), // Default: today
        initial_capital: 100000,
        z_score_window: 20,
        entry_z_threshold: 2.0,
        exit_z_threshold: 0.5,
    };
    const [backtestParams, setBacktestParams] = useState<reportService.GenerateBacktestReportRequest>(initialBacktestParams);
    const [backtestTickersInput, setBacktestTickersInput] = useState<string>(''); // User input for tickers, comma-separated for easy input

    // State for Report Details Dialog (viewing results of a selected report)
    const [selectedReportDetails, setSelectedReportDetails] = useState<reportService.Report | null>(null);
    const [openReportDetailsDialog, setOpenReportDetailsDialog] = useState(false);
    const [equityCurveData, setEquityCurveData] = useState<any[]>([]);
    const [equityCurveLayout, setEquityCurveLayout] = useState<any>({});

    /**
     * Fetches the list of all generated reports from the backend.
     * Uses useCallback to memoize the function, re-fetching if isAuthenticated changes.
     */
    const fetchReports = useCallback(async () => {
        if (!isAuthenticated) return; // Do not fetch if user is not logged in
        setIsLoading(true);
        setError(null);
        // setSuccessMessage(null); // Optionally clear success messages on each refresh action
        try {
            const fetchedReports = await reportService.getGeneratedReports();
            setReports(fetchedReports);
        } catch (err: any) {
            setError(err.message || 'Failed to fetch reports list.');
            setReports([]); // Clear any previously loaded reports on error
        } finally {
            setIsLoading(false);
        }
    }, [isAuthenticated]); // Re-run if authentication status changes

    useEffect(() => {
        fetchReports(); // Initial fetch when the component mounts (if authenticated)
    }, [fetchReports]);

    /**
     * Handles the request to generate a summary report (Daily/Weekly).
     */
    const handleRequestSummaryReport = async () => {
        setError(null); setSuccessMessage(null); setIsLoading(true);
        try {
            const result = await reportService.requestSummaryReportGeneration({ report_type: summaryReportType });
            setSuccessMessage(result.message || `Requested ${summaryReportType.toLowerCase()} summary. Task ID: ${result.task_id}.`);
            fetchReports(); // Refresh the list of reports to show the new PENDING report
        } catch (err: any) { setError(err.message || 'Failed to request summary report.');
        } finally { setIsLoading(false); }
    };

    /**
     * Generic handler for changes in the backtest parameter form fields.
     * Updates the `backtestParams` state based on input name and value.
     */
    const handleBacktestParamsChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement> | SelectChangeEvent<string>) => {
        const { name, value } = event.target;
        const numFields = ['initial_capital', 'z_score_window', 'entry_z_threshold', 'exit_z_threshold'];
        const parsedValue = numFields.includes(name) ? (value === '' ? undefined : parseFloat(value)) : value;
        setBacktestParams(prev => ({ ...prev, [name as string]: parsedValue }));
    };

    /**
     * Handler for date changes in the backtest form (Start Date, End Date).
     * @param field - The specific date field to update ('start_date' or 'end_date').
     * @returns A function that takes a Moment date object (or null) and updates the state.
     */
    const handleBacktestDateChange = (field: 'start_date' | 'end_date') => (date: Moment | null) => {
        setBacktestParams(prev => ({ ...prev, [field]: date ? date.format('YYYY-MM-DD') : initialBacktestParams[field] }));
    };

    /**
     * Handler for ticker input changes in the backtest form.
     * Updates both the raw input string and the parsed tickers array in `backtestParams`.
     */
    const handleBacktestTickersChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        setBacktestTickersInput(event.target.value);
        const tickersArray = event.target.value.split(',').map(t => t.trim().toUpperCase()).filter(t => t);
        setBacktestParams(prev => ({ ...prev, tickers: tickersArray }));
    };

    /**
     * Handles the request to generate a backtest report.
     * Performs client-side validation before calling the report generation service.
     */
    const handleRequestBacktestReport = async () => {
        setError(null); setSuccessMessage(null);
        // Basic client-side validation
        if (backtestParams.tickers.length !== 2) {
            setError("Backtesting requires exactly one pair of two tickers (Y,X). Please provide comma-separated tickers.");
            return;
        }
        if (!backtestParams.start_date || !backtestParams.end_date) {
            setError("Start date and end date are required for backtest.");
            return;
        }
        setIsLoading(true);
        try {
            const paramsToSubmit = {
                ...backtestParams,
                report_name: backtestParams.report_name || `Backtest ${backtestParams.tickers.join('-')} ${new Date().toISOString().split('T')[0]}`
            };
            const result = await reportService.requestBacktestReportGeneration(paramsToSubmit);
            setSuccessMessage(result.message || `Requested backtest for ${paramsToSubmit.strategy_name}. Task ID: ${result.task_id}.`);
            fetchReports(); // Refresh list
        } catch (err: any) { setError(err.message || 'Failed to request backtest report.');
        } finally { setIsLoading(false); }
    };

    /**
     * Handles report file downloads.
     * Constructs download URL or uses provided URL from report metadata.
     * @param report - The report object containing download URL information.
     * @param format - The desired file format ('pdf' or 'csv').
     */
    const handleDownload = (report: reportService.Report, format: 'pdf' | 'csv') => {
        const downloadUrlKey = `download_url_${format}` as keyof reportService.Report;
        const downloadUrl = report[downloadUrlKey];

        if (downloadUrl) {
             window.open(downloadUrl.startsWith('http') ? downloadUrl : `${process.env.REACT_APP_API_BASE_URL || ''}${downloadUrl}`, '_blank');
        } else {
            const fallbackUrl = `/api/v1/reports/${report.id}/download/${format}`;
            window.open(fallbackUrl, '_blank');
        }
    };

    /**
     * Opens the dialog to display detailed results of a selected report.
     * For backtest reports, it prepares data for an equity curve chart.
     * @param report - The report object whose details are to be viewed.
     */
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

            {isLoading && <Box sx={{ display: 'flex', justifyContent: 'center', my: 1 }}><CircularProgress size={24} /></Box>}
            {error && <Alert severity="error" sx={{ my: 2, width: '100%' }} onClose={() => setError(null)}>{error}</Alert>}
            {successMessage && <Alert severity="success" sx={{ my: 2, width: '100%' }} onClose={() => setSuccessMessage(null)}>{successMessage}</Alert>}

            {/* Form Grid: Summary Report and Backtest Report Request Forms */}
            <Grid container spacing={3}>
                {/* Summary Report Request Form */}
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
                         <Button variant="contained" startIcon={<PlayArrowIcon />} onClick={handleRequestSummaryReport} disabled={isLoading} sx={{mt:1}}>Generate Summary</Button>
                    </Paper>
                </Grid>

                {/* Backtest Report Request Form */}
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
                        <Button variant="contained" startIcon={<PlayArrowIcon />} onClick={handleRequestBacktestReport} disabled={isLoading} sx={{mt:2}}>Run Backtest</Button>
                    </Paper>
                </Grid>
            </Grid>

            {/* Display Area for Generated Reports */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', my: 2 }}>
                <Typography variant="h5" gutterBottom>Generated Reports</Typography>
                <Button variant="outlined" startIcon={<RefreshIcon />} onClick={fetchReports} disabled={isLoading}>Refresh List</Button>
            </Box>
            <TableContainer component={Paper}>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>Name/ID</TableCell><TableCell>Type</TableCell><TableCell>Generated At</TableCell>
                            <TableCell>Status</TableCell><TableCell align="center">Actions</TableCell>
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
                                <TableCell>{report.status || 'N/A'}</TableCell>
                                <TableCell align="center">
                                    {report.status === "COMPLETED" && (
                                        <>
                                        <Tooltip title="View Results"><IconButton size="small" onClick={() => handleViewReportDetails(report)} color="primary"><AssessmentIcon /></IconButton></Tooltip>
                                        {report.download_url_pdf && <Tooltip title="Download PDF"><IconButton size="small" onClick={() => handleDownload(report, 'pdf')}><FileDownloadIcon /></IconButton></Tooltip>}
                                        {report.download_url_csv && <Tooltip title="Download CSV"><IconButton size="small" onClick={() => handleDownload(report, 'csv')}><FileDownloadIcon /></IconButton></Tooltip>}
                                        </>
                                    )}
                                    {(report.status === "PENDING" || report.status === "PROCESSING") && <CircularProgress size={20} titleAccess={report.status} />}
                                    {report.status === "FAILED" && <Tooltip title={report.error_message || "Failed"}><Typography variant="caption" color="error">Failed</Typography></Tooltip>}
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            {/* Dialog for Displaying Report Details, including Equity Curve */}
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

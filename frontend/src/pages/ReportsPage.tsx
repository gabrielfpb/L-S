import React, { useEffect, useState, useCallback } from 'react';
import {
    Typography, Container, Paper, Box, CircularProgress, Alert, Button,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, IconButton,
    Grid, TextField, Select, MenuItem, FormControl, InputLabel, SelectChangeEvent
} from '@mui/material';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import RefreshIcon from '@mui/icons-material/Refresh';
import * as reportService from '../services/reportService'; // Import report service
import { useAuth } from '../contexts/AuthContext'; // If reports are user-specific

const ReportsPage: React.FC = () => {
    const [reports, setReports] = useState<reportService.Report[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    const { isAuthenticated } = useAuth();

    // State for Summary Report Request
    const [summaryReportType, setSummaryReportType] = useState<"DAILY" | "WEEKLY">("DAILY");

    // State for Backtest Report Request
    const [backtestParams, setBacktestParams] = useState<reportService.GenerateBacktestReportRequest>({
        strategy_name: 'default_pair_trading',
        tickers: [],
        start_date: new Date(new Date().setFullYear(new Date().getFullYear() - 1)).toISOString().split('T')[0],
        end_date: new Date().toISOString().split('T')[0],
        initial_capital: 100000,
    });
    const [backtestTickersInput, setBacktestTickersInput] = useState<string>('');


    const fetchReports = useCallback(async () => {
        if (!isAuthenticated) return;
        setIsLoading(true);
        setError(null);
        setSuccessMessage(null); // Clear success message on refresh
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

    const handleRequestSummaryReport = async () => {
        setError(null);
        setSuccessMessage(null);
        setIsLoading(true);
        try {
            const result = await reportService.requestSummaryReportGeneration({ report_type: summaryReportType });
            setSuccessMessage(result.message || `Requested ${summaryReportType.toLowerCase()} summary report. Task ID: ${result.task_id}. Refresh list after a while.`);
            // Consider a small delay then fetchReports() or implement polling for task status
        } catch (err: any) {
            setError(err.message || 'Failed to request summary report.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleBacktestParamsChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement> | SelectChangeEvent<string>) => {
        const { name, value } = event.target;
        const isNumberField = name === 'initial_capital';
        setBacktestParams(prev => ({
            ...prev,
            [name as string]: isNumberField ? (value === '' ? undefined : parseFloat(value)) : value
        }));
    };

    const handleBacktestTickersChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        setBacktestTickersInput(event.target.value);
        const tickersArray = event.target.value.split(',').map(t => t.trim()).filter(t => t);
        setBacktestParams(prev => ({ ...prev, tickers: tickersArray }));
    };

    const handleRequestBacktestReport = async () => {
        setError(null);
        setSuccessMessage(null);

        if(backtestParams.tickers.length === 0){ // Basic validation
            setError("Please provide at least one ticker for backtesting. For pairs, provide two.");
            return;
        }
        // Example: if strategy 'default_pair_trading' requires exactly 2 tickers
        if(backtestParams.strategy_name === 'default_pair_trading' && backtestParams.tickers.length !== 2){
            setError("The selected pair trading strategy requires exactly two tickers (e.g., Y,X).");
            return;
        }
        setIsLoading(true);
        try {
            const result = await reportService.requestBacktestReportGeneration(backtestParams);
            setSuccessMessage(result.message || `Requested backtest report for ${backtestParams.strategy_name}. Task ID: ${result.task_id}. Refresh list after a while.`);
        } catch (err: any) {
            setError(err.message || 'Failed to request backtest report.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleDownload = (report: reportService.Report, format: 'pdf' | 'csv') => {
        const url = format === 'pdf' ? report.download_url_pdf : report.download_url_csv;
        if (url) {
            // Assuming backend provides a relative path like /static/reports/report.pdf
            // Prepend API base URL if it's not a full URL and served by backend API
            // For now, assuming it's a full URL or relative to frontend public path (less likely for dynamic reports)
            // If it's an API endpoint, it might be apiClient.get(url, { responseType: 'blob' })...
            let fullUrl = url;
            if (!url.startsWith('http://') && !url.startsWith('https://') && process.env.REACT_APP_API_BASE_URL) {
                // Example: if url is '/static/reports/file.pdf' and API is 'http://localhost:8000/api/v1'
                // This needs to be adjusted based on how backend serves files.
                // If files are served from FastAPI's /static route at root of backend, then:
                // fullUrl = `${process.env.REACT_APP_BACKEND_ROOT_URL}${url}`; // Assuming backend root is different from API base
            }
            window.open(fullUrl, '_blank');

        } else {
            setError(`Download URL for ${format.toUpperCase()} not available for report ${report.id}.`);
        }
    };

    if (!isAuthenticated) {
        return (
            <Container>
                <Alert severity="warning" sx={{ mt: 3 }}>Please login to manage and view reports.</Alert>
            </Container>
        );
    }

    return (
        <Container maxWidth="lg">
            <Typography variant="h4" component="h1" gutterBottom sx={{ my: 2 }}>
                Reports Center
            </Typography>

            {/* Global feedback messages, distinct from form-specific errors if needed */}
            {isLoading && <Box sx={{ display: 'flex', justifyContent: 'center', my: 1 }}><CircularProgress size={24} /></Box>}
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
                        <Button variant="contained" startIcon={<PlayArrowIcon />} onClick={handleRequestSummaryReport} disabled={isLoading} sx={{mt:1}}>
                            Generate Summary
                        </Button>
                    </Paper>
                </Grid>

                <Grid item xs={12} md={6}>
                    <Paper sx={{ p: 2, mb: 3 }}>
                        <Typography variant="h6" gutterBottom>Request Backtest Report</Typography>
                        <TextField name="strategy_name" label="Strategy Name" value={backtestParams.strategy_name} onChange={handleBacktestParamsChange} fullWidth margin="normal" />
                        <TextField label="Tickers (e.g., Y,X for pair)" value={backtestTickersInput} onChange={handleBacktestTickersChange} fullWidth margin="normal" helperText="Comma-separated, e.g. PETR4.SA,VALE3.SA" />
                        <Grid container spacing={2}>
                            <Grid item xs={6}><TextField name="start_date" label="Start Date" type="date" value={backtestParams.start_date} onChange={handleBacktestParamsChange} fullWidth margin="normal" InputLabelProps={{ shrink: true }} /></Grid>
                            <Grid item xs={6}><TextField name="end_date" label="End Date" type="date" value={backtestParams.end_date} onChange={handleBacktestParamsChange} fullWidth margin="normal" InputLabelProps={{ shrink: true }} /></Grid>
                        </Grid>
                        <TextField name="initial_capital" label="Initial Capital" type="number" value={backtestParams.initial_capital} onChange={handleBacktestParamsChange} fullWidth margin="normal" />
                        <Button variant="contained" startIcon={<PlayArrowIcon />} onClick={handleRequestBacktestReport} disabled={isLoading} sx={{mt:1}}>
                            Run Backtest
                        </Button>
                    </Paper>
                </Grid>
            </Grid>

            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', my: 2 }}>
                <Typography variant="h5" gutterBottom>Generated Reports</Typography>
                <Button variant="outlined" startIcon={<RefreshIcon />} onClick={fetchReports} disabled={isLoading}>Refresh List</Button>
            </Box>
            <TableContainer component={Paper}>
                <Table aria-label="generated reports table" size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>Report ID</TableCell>
                            <TableCell>Type</TableCell>
                            <TableCell>Generated At</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell>File Name</TableCell>
                            <TableCell align="center">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {reports.length === 0 && !isLoading && (
                            <TableRow><TableCell colSpan={6} align="center">No reports found or generated yet.</TableCell></TableRow>
                        )}
                        {reports.map((report) => (
                            <TableRow key={report.id} hover>
                                <TableCell>{report.id}</TableCell>
                                <TableCell>{report.report_type}</TableCell>
                                <TableCell>{new Date(report.generated_at).toLocaleString()}</TableCell>
                                <TableCell>{report.status || 'N/A'}</TableCell>
                                <TableCell>{report.file_name || 'N/A'}</TableCell>
                                <TableCell align="center">
                                    {report.status === "COMPLETED" && report.download_url_pdf && (
                                        <Tooltip title="Download PDF">
                                            <IconButton size="small" onClick={() => handleDownload(report, 'pdf')} color="primary">
                                                <FileDownloadIcon /> <Typography variant="caption" sx={{ml:0.5}}>PDF</Typography>
                                            </IconButton>
                                        </Tooltip>
                                    )}
                                    {report.status === "COMPLETED" && report.download_url_csv && (
                                        <Tooltip title="Download CSV">
                                            <IconButton size="small" onClick={() => handleDownload(report, 'csv')} color="secondary">
                                                <FileDownloadIcon /> <Typography variant="caption" sx={{ml:0.5}}>CSV</Typography>
                                            </IconButton>
                                        </Tooltip>
                                    )}
                                    {report.status === "PENDING" && (
                                        <Typography variant="caption" color="textSecondary">Processing...</Typography>
                                    )}
                                     {report.status !== "COMPLETED" && report.status !== "PENDING" && (!report.download_url_csv && !report.download_url_pdf) && (
                                        <Typography variant="caption" color="textSecondary">-</Typography> // No actions if not completed/pending or no URLs
                                    )}
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>
        </Container>
    );
};

export default ReportsPage;

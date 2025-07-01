import React, { useEffect, useState } from 'react';
import {
    Typography, Container, Paper, Box, CircularProgress, Alert,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Button,
    TextField, Grid, Tooltip
} from '@mui/material';
import Plot from 'react-plotly.js';
import {
    identifyCointegratedPairs, IdentifiedPairData, IdentifyPairsRequest,
    getPairZScore, PairZScoreRequest, PairZScoreResponse, // Original ZScore for table
    getHistoricalPairData, HistoricalPairDataRequestFE, HistoricalPairDataResponseFE // For detailed chart
} from '../services/cointegrationService';
import InfoIcon from '@mui/icons-material/Info';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterMoment } from '@mui/x-date-pickers/AdapterMoment';
import moment, { Moment } from 'moment'; // Import Moment for date handling


const DashboardPage: React.FC = () => {
    const [identifiedPairs, setIdentifiedPairs] = useState<IdentifiedPairData[]>([]);
    const [isLoadingPairs, setIsLoadingPairs] = useState<boolean>(false);
    const [errorPairs, setErrorPairs] = useState<string | null>(null);
    const [summaryMessage, setSummaryMessage] = useState<string>('');

    const [selectedPairForChart, setSelectedPairForChart] = useState<IdentifiedPairData | null>(null);
    const [chartPlotData, setChartPlotData] = useState<any[]>([]); // For Plotly data traces
    const [chartPlotLayout, setChartPlotLayout] = useState<any>({}); // For Plotly layout
    const [isLoadingChart, setIsLoadingChart] = useState<boolean>(false);
    const [errorChart, setErrorChart] = useState<string | null>(null);

    const defaultTickers = ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA"];
    const [tickersToAnalyze, setTickersToAnalyze] = useState<string>(defaultTickers.join(', '));
    const [lastUpdatedPairs, setLastUpdatedPairs] = useState<Date | null>(null); // New state for timestamp

    // State for chart parameters
    const [chartStartDate, setChartStartDate] = useState<Moment | null>(moment().subtract(1, 'year'));
    const [chartEndDate, setChartEndDate] = useState<Moment | null>(moment());
    const [chartZScoreWindow, setChartZScoreWindow] = useState<number>(20);


    // Fetches identified cointegrated pairs based on the current `tickersToAnalyze`
    const handleIdentifyPairs = async (isRefresh: boolean = false) => {
        if (!isRefresh) { // If not just a refresh, clear previous chart selection
            setSelectedPairForChart(null);
            setChartPlotData([]);
            setChartPlotLayout({});
        }
        setIsLoadingPairs(true);
        setErrorPairs(null);
        // Do not clear identifiedPairs on refresh, allow new data to replace it for smoother UX
        // if (!isRefresh) setIdentifiedPairs([]);
        setSummaryMessage('');
        try {
            const params: IdentifyPairsRequest = {
                tickers: tickersToAnalyze.split(',').map(t => t.trim().toUpperCase()).filter(t => t),
            };
            if (params.tickers.length < 2) {
                setErrorPairs("Please provide at least two tickers.");
                setIsLoadingPairs(false);
                return;
            }
            const response = await identifyCointegratedPairs(params);
            setIdentifiedPairs(response.pairs);
            setSummaryMessage(response.summary_message);
            setLastUpdatedPairs(new Date()); // Set timestamp on successful fetch/refresh
        } catch (err: any) {
            setErrorPairs(err.message || 'Failed to fetch cointegrated pairs.');
            // Do not clear lastUpdatedPairs on error, so user knows when the last *successful* data was from
        } finally {
            setIsLoadingPairs(false);
        }
    };

    // Function to fetch and display Z-score in table (original simple one)
    // This function is currently not used directly as detailed chart fetching replaced simple Z-score display.
    // It can be removed or adapted if a quick Z-score preview in the table becomes a requirement again.
    const fetchAndDisplaySimpleZScore = async (pair: IdentifiedPairData) => {
        // Placeholder for any logic if needed for quick Z-score previews.
    };

    // Fetches and displays detailed historical data (spread, Z-score, bands) for the selected pair
    const handleViewPairDetails = async (pair: IdentifiedPairData | null = selectedPairForChart) => {
        if (!pair) {
            setErrorChart("No pair selected to display details for.");
            return;
        }
        setSelectedPairForChart(pair); // Ensure it's set if called by refresh button
        setIsLoadingChart(true);
        setErrorChart(null);
        setChartPlotData([]);
        setChartPlotLayout({});

        if (!chartStartDate || !chartEndDate || !chartStartDate.isValid() || !chartEndDate.isValid()) {
            setErrorChart("Please select valid start and end dates for the chart.");
            setIsLoadingChart(false);
            return;
        }
        if (chartZScoreWindow < 2) {
            setErrorChart("Z-Score window must be at least 2.");
            setIsLoadingChart(false);
            return;
        }

        try {
            const params: HistoricalPairDataRequestFE = {
                ticker_y: pair.pair_yx[0],
                ticker_x: pair.pair_yx[1],
                start_date: chartStartDate.format('YYYY-MM-DD'), // Dates formatted from Moment objects
                end_date: chartEndDate.format('YYYY-MM-DD'),
                z_score_window: chartZScoreWindow,
            };
            const historicalData = await getHistoricalPairData(params); // API call

            if (historicalData.error) {
                setErrorChart(historicalData.error);
                setChartPlotData([]); // Clear data on error
                return;
            }

            // Convert ISO timestamp strings from backend to Date objects for Plotly
            const timestamps = historicalData.timestamps.map(t => new Date(t));

            // Construct Plotly data traces
            const newChartPlotData: Partial<Plotly.PlotData>[] = [
                { // Trace for the spread
                    x: timestamps, y: historicalData.spread, type: 'scatter', mode: 'lines', name: 'Spread (Y - Beta*X)',
                    line: { color: 'blue' }, yaxis: 'y1'
                },
                { // Trace for rolling mean of spread
                    x: timestamps, y: historicalData.spread_mean, type: 'scatter', mode: 'lines', name: 'Spread Mean',
                    line: { color: 'orange', dash: 'dash' }, yaxis: 'y1'
                },
                { // Trace for +2 standard deviation band
                    x: timestamps, y: historicalData.spread_std_dev_upper_2, type: 'scatter', mode: 'lines', name: '+2 Std Dev',
                    line: { color: 'rgba(255,0,0,0.4)', dash: 'dot' }, fill: 'tonexty', fillcolor: 'rgba(255,0,0,0.05)', yaxis: 'y1' // Fill to next Y trace
                },
                { // Trace for -2 standard deviation band
                    x: timestamps, y: historicalData.spread_std_dev_lower_2, type: 'scatter', mode: 'lines', name: '-2 Std Dev',
                    line: { color: 'rgba(255,0,0,0.4)', dash: 'dot' }, fill: 'tonexty', fillcolor: 'rgba(255,0,0,0.05)', yaxis: 'y1' // Fill to next Y trace (which is the +2 band)
                },
                { // Trace for Z-Score, plotted on a secondary Y-axis
                    x: timestamps, y: historicalData.z_score, type: 'scatter', mode: 'lines', name: 'Z-Score',
                    yaxis: 'y2', line: { color: 'green' }
                }
            ];
            setChartPlotData(newChartPlotData);

            // Configure Plotly layout
            setChartPlotLayout({
                title: `Spread & Z-Score: ${pair.pair_yx[0]} / ${pair.pair_yx[1]} (Hedge Ratio: ${historicalData.calculated_hedge_ratio_beta_x?.toFixed(4) ?? 'N/A'})`,
                autosize: true,
                height: 500, // Specify chart height
                xaxis: { title: 'Date', type: 'date', automargin: true },
                yaxis: { title: 'Spread Value', automargin: true, domain: [0.3, 1] }, // Main chart for spread, occupying top 70%
                yaxis2: { // Secondary Y-axis for Z-score
                    title: 'Z-Score',
                    overlaying: 'y', // Overlay on y1
                    side: 'right',
                    automargin: true,
                    domain: [0, 0.25], // Z-score chart at the bottom 25%
                    showgrid: false,
                    zeroline: true,
                    zerolinecolor: 'rgba(0,0,0,0.5)'
                },
                legend: { x: 0.5, y: 1.15, xanchor: 'center', orientation: 'h' }, // Legend above chart
                margin: { l: 50, r: 50, b: 50, t: 80, pad: 4 },
                hovermode: 'x unified' // Unified hover info across y-axes
            });

        } catch (err: any) {
            setErrorChart(err.message || `Failed to fetch historical details for ${pair.pair_yx[0]}/${pair.pair_yx[1]}.`);
            setChartPlotData([]);
        } finally {
            setIsLoadingChart(false);
        }
    };


    return (
        <Container maxWidth="xl"> {/* Use "xl" for wider content area */}
            <Typography variant="h4" component="h1" gutterBottom sx={{ my: 2 }}>
                Cointegration Dashboard
            </Typography>

            {/* Section for identifying pairs */}
            <Paper sx={{ p: 2, mb: 3 }}>
                <Typography variant="h6" gutterBottom>Identify Cointegrated Pairs</Typography>
                <TextField label="Tickers (comma-separated)" value={tickersToAnalyze} onChange={(e) => setTickersToAnalyze(e.target.value)}
                    fullWidth margin="normal" helperText="e.g., PETR4.SA, VALE3.SA, ITUB4.SA" disabled={isLoadingPairs} />
                <Box sx={{display: 'flex', gap: 1, alignItems: 'center', my:1}}>
                    <Button variant="contained" onClick={() => handleIdentifyPairs(false)} disabled={isLoadingPairs}>
                        {isLoadingPairs ? (lastUpdatedPairs ? 'Re-Identifying...' : 'Identifying...') : 'Identify / Re-Identify Pairs'}
                    </Button>
                </Box>
            </Paper>

            {/* Loading and error/summary messages for pair identification */}
            {isLoadingPairs && identifiedPairs.length === 0 && <Box sx={{ display: 'flex', justifyContent: 'center', my: 3 }}><CircularProgress /></Box>}
            {errorPairs && <Alert severity="error" sx={{ my: 2 }} onClose={() => setErrorPairs(null)}>{errorPairs}</Alert>}
            {summaryMessage && !errorPairs && <Alert severity="info" sx={{ my: 2 }} onClose={() => setSummaryMessage('')}>{summaryMessage}</Alert>}

            {/* Identified Opportunities Table Section */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 3, mb: 1 }}>
                <Typography variant="h5" gutterBottom component="div">
                    Identified Opportunities
                </Typography>
                {identifiedPairs.length > 0 && ( // Show refresh button only if there are pairs
                    <Button
                        variant="text"
                        size="small"
                        startIcon={isLoadingPairs ? <CircularProgress size={20} /> : <RefreshIcon />}
                        onClick={() => handleIdentifyPairs(true)} // isRefresh = true
                        disabled={isLoadingPairs}
                    >
                        {isLoadingPairs ? 'Refreshing...' : 'Refresh List & Z-Scores'}
                    </Button>
                )}
            </Box>
            {lastUpdatedPairs && identifiedPairs.length > 0 && ( // Show last updated time if available
                <Typography variant="caption" display="block" color="textSecondary" gutterBottom sx={{mb:2}}>
                    Last updated: {lastUpdatedPairs.toLocaleString()}
                </Typography>
            )}
            <TableContainer component={Paper} sx={{mb:3}}>
                {/* ... Table structure ... */}
            </TableContainer>

            {/* Pair Historical Chart Section */}
            <Typography variant="h5" gutterBottom sx={{mt:3}}>Pair Historical Chart</Typography>
            {/* Chart parameters form */}
            <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6">Chart Parameters</Typography>
                <Grid container spacing={2} alignItems="center" sx={{mt:0.5, mb:1.5}}>
                    <LocalizationProvider dateAdapter={AdapterMoment}>
                        <Grid item xs={12} sm={6} md={3}>
                            <DatePicker label="Start Date" value={chartStartDate} onChange={(newValue) => setChartStartDate(newValue)} sx={{width: '100%'}} />
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                             <DatePicker label="End Date" value={chartEndDate} onChange={(newValue) => setChartEndDate(newValue)} sx={{width: '100%'}} />
                        </Grid>
                    </LocalizationProvider>
                    <Grid item xs={12} sm={6} md={3}>
                         <TextField label="Z-Score Window" type="number" value={chartZScoreWindow}
                            onChange={(e) => setChartZScoreWindow(parseInt(e.target.value, 10) || 20)} fullWidth
                            InputProps={{ inputProps: { min: 2, max: 200 } }} helperText="For rolling calculations" />
                    </Grid>
                    <Grid item xs={12} sm={6} md={3} sx={{display: 'flex', alignItems: 'flex-end'}}>
                        {selectedPairForChart &&  // Only show refresh button if a pair is selected for charting
                            <Button variant="contained" onClick={() => handleViewPairDetails(selectedPairForChart)} disabled={isLoadingChart || !chartStartDate || !chartEndDate} fullWidth>
                                {isLoadingChart ? 'Loading Chart...' : `Refresh Chart: ${selectedPairForChart.pair_yx[0]}/${selectedPairForChart.pair_yx[1]}`}
                            </Button>}
                    </Grid>
                </Grid>
            </Paper>

            {/* Chart display area */}
            <Paper sx={{ p: 2, minHeight: 500, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
                {isLoadingChart && <CircularProgress />}
                {errorChart && !isLoadingChart && <Alert severity="error" sx={{width: '100%'}} onClose={() => setErrorChart(null)}>{errorChart}</Alert>}
                {!isLoadingChart && !errorChart && selectedPairForChart && chartPlotData.length > 0 && (
                    <Plot data={chartPlotData} layout={chartPlotLayout} useResizeHandler={true} style={{ width: '100%', height: '500px' }} config={{ responsive: true }}/>
                )}
                {!isLoadingChart && !selectedPairForChart && !errorChart && ( // Initial state, no pair selected
                    <Typography sx={{textAlign: 'center', color: 'text.secondary'}}>Select a pair from the table and set parameters to view historical chart.</Typography>)}
                 {!isLoadingChart && selectedPairForChart && chartPlotData.length === 0 && !errorChart && ( // Pair selected, but no data (e.g., after error or if data was empty)
                    <Typography sx={{textAlign: 'center', color: 'text.secondary'}}>No chart data to display. Try adjusting parameters or ensure data is available.</Typography>)}
            </Paper>
        </Container>
    );
};
                {
                    x: timestamps, y: historicalData.spread_mean, type: 'scatter', mode: 'lines', name: 'Spread Mean',
                    line: { color: 'orange', dash: 'dash' }, yaxis: 'y1'
                },
                {
                    x: timestamps, y: historicalData.spread_std_dev_upper_2, type: 'scatter', mode: 'lines', name: '+2 Std Dev',
                    line: { color: 'rgba(255,0,0,0.4)', dash: 'dot' }, fill: 'tonexty', fillcolor: 'rgba(255,0,0,0.05)', yaxis: 'y1'
                },
                {
                    x: timestamps, y: historicalData.spread_std_dev_lower_2, type: 'scatter', mode: 'lines', name: '-2 Std Dev',
                    line: { color: 'rgba(255,0,0,0.4)', dash: 'dot' }, fill: 'tonexty', fillcolor: 'rgba(255,0,0,0.05)', yaxis: 'y1'
                },
                {
                    x: timestamps, y: historicalData.z_score, type: 'scatter', mode: 'lines', name: 'Z-Score',
                    yaxis: 'y2', line: { color: 'green' }
                }
            ];
            setChartPlotData(newChartPlotData);

            setChartPlotLayout({
                title: `Spread & Z-Score: ${pair.pair_yx[0]} / ${pair.pair_yx[1]} (Hedge Ratio: ${historicalData.calculated_hedge_ratio_beta_x?.toFixed(4) ?? 'N/A'})`,
                autosize: true,
                height: 500,
                xaxis: { title: 'Date', type: 'date', automargin: true },
                yaxis: { title: 'Spread Value', automargin: true, domain: [0.3, 1] }, // Main chart for spread
                yaxis2: { title: 'Z-Score', overlaying: 'y', side: 'right', automargin: true, domain: [0, 0.25], showgrid: false, zeroline: true, zerolinecolor: 'rgba(0,0,0,0.5)'}, // Z-score chart below
                legend: { x: 0.5, y: 1.15, xanchor: 'center', orientation: 'h' },
                margin: { l: 50, r: 50, b: 50, t: 80, pad: 4 }, // Adjust margins
                hovermode: 'x unified'
            });

        } catch (err: any) {
            setErrorChart(err.message || `Failed to fetch historical details for ${pair.pair_yx[0]}/${pair.pair_yx[1]}.`);
            setChartPlotData([]);
        } finally {
            setIsLoadingChart(false);
        }
    };


    return (
        <Container maxWidth="xl"> {/* Use "xl" for wider content area */}
            <Typography variant="h4" component="h1" gutterBottom sx={{ my: 2 }}>
                Cointegration Dashboard
            </Typography>

            <Paper sx={{ p: 2, mb: 3 }}>
                <Typography variant="h6" gutterBottom>Identify Cointegrated Pairs</Typography>
                <TextField label="Tickers (comma-separated)" value={tickersToAnalyze} onChange={(e) => setTickersToAnalyze(e.target.value)}
                    fullWidth margin="normal" helperText="e.g., PETR4.SA, VALE3.SA, ITUB4.SA" disabled={isLoadingPairs} />
                <Box sx={{display: 'flex', gap: 1, alignItems: 'center', my:1}}>
                    <Button variant="contained" onClick={() => handleIdentifyPairs(false)} disabled={isLoadingPairs}>
                        {isLoadingPairs ? (lastUpdatedPairs ? 'Re-Identifying...' : 'Identifying...') : 'Identify / Re-Identify Pairs'}
                    </Button>
                </Box>
            </Paper>

            {/* Show main loading indicator only if no data is present yet, otherwise refresh is more subtle */}
            {isLoadingPairs && identifiedPairs.length === 0 && <Box sx={{ display: 'flex', justifyContent: 'center', my: 3 }}><CircularProgress /></Box>}
            {errorPairs && <Alert severity="error" sx={{ my: 2 }} onClose={() => setErrorPairs(null)}>{errorPairs}</Alert>}
            {summaryMessage && !errorPairs && <Alert severity="info" sx={{ my: 2 }} onClose={() => setSummaryMessage('')}>{summaryMessage}</Alert>}

            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 3, mb: 1 }}>
                <Typography variant="h5" gutterBottom component="div">
                    Identified Opportunities
                </Typography>
                {identifiedPairs.length > 0 && (
                    <Button
                        variant="text"
                        size="small"
                        startIcon={isLoadingPairs ? <CircularProgress size={20} /> : <RefreshIcon />}
                        onClick={() => handleIdentifyPairs(true)}
                        disabled={isLoadingPairs}
                    >
                        {isLoadingPairs ? 'Refreshing...' : 'Refresh List & Z-Scores'}
                    </Button>
                )}
            </Box>
            {lastUpdatedPairs && identifiedPairs.length > 0 && (
                <Typography variant="caption" display="block" color="textSecondary" gutterBottom sx={{mb:2}}>
                    Last updated: {lastUpdatedPairs.toLocaleString()}
                </Typography>
            )}
            <TableContainer component={Paper} sx={{mb:3}}>
                <Table aria-label="cointegrated pairs table" size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>Pair (Y / X)</TableCell>
                            <TableCell align="right">Hedge Ratio</TableCell>
                            <TableCell align="right">P-Value</TableCell>
                            <TableCell align="right">Z-Score (Spread)</TableCell>
                            <TableCell align="right">Observations</TableCell>
                            <TableCell align="center">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {identifiedPairs.length === 0 && !isLoadingPairs && (
                            <TableRow><TableCell colSpan={6} align="center">No cointegrated pairs found or identified yet.</TableCell></TableRow>
                        )}
                        {identifiedPairs.map((pair, index) => (
                            <TableRow key={`${pair.pair_yx[0]}-${pair.pair_yx[1]}-${index}`} hover selected={selectedPairForChart?.pair_yx[0] === pair.pair_yx[0] && selectedPairForChart?.pair_yx[1] === pair.pair_yx[1]}>
                                <TableCell component="th" scope="row">{pair.pair_yx[0]} / {pair.pair_yx[1]}</TableCell>
                                <TableCell align="right">{pair.hedge_ratio_beta_x?.toFixed(4) || 'N/A'}</TableCell>
                                <TableCell align="right">{pair.p_value.toFixed(4)}</TableCell>
                                <TableCell align="right" sx={{ fontWeight: Math.abs(pair.current_zscore_of_spread || 0) > 1.5 ? 'bold' : 'normal', color: Math.abs(pair.current_zscore_of_spread || 0) > 2 ? 'red' : 'inherit' }}>
                                    {pair.current_zscore_of_spread?.toFixed(2) || 'N/A'}
                                    {Math.abs(pair.current_zscore_of_spread || 0) > 2 &&
                                        <Tooltip title="Potential Signal (Z-score > |2|)"><InfoIcon fontSize="inherit" sx={{verticalAlign: 'middle', ml:0.5, cursor: 'help'}} color="error"/></Tooltip>}
                                </TableCell>
                                <TableCell align="right">{pair.n_observations_in_test}</TableCell>
                                <TableCell align="center">
                                    <Button size="small" onClick={() => handleViewPairDetails(pair)} variant="outlined">Chart Details</Button>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            <Typography variant="h5" gutterBottom sx={{mt:3}}>Pair Historical Chart</Typography>
            <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6">Chart Parameters</Typography>
                <Grid container spacing={2} alignItems="center" sx={{mt:0.5, mb:1.5}}>
                    <LocalizationProvider dateAdapter={AdapterMoment}>
                        <Grid item xs={12} sm={6} md={3}>
                            <DatePicker label="Start Date" value={chartStartDate} onChange={(newValue) => setChartStartDate(newValue)} sx={{width: '100%'}} />
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                             <DatePicker label="End Date" value={chartEndDate} onChange={(newValue) => setChartEndDate(newValue)} sx={{width: '100%'}} />
                        </Grid>
                    </LocalizationProvider>
                    <Grid item xs={12} sm={6} md={3}>
                         <TextField label="Z-Score Window" type="number" value={chartZScoreWindow}
                            onChange={(e) => setChartZScoreWindow(parseInt(e.target.value, 10) || 20)} fullWidth
                            InputProps={{ inputProps: { min: 2, max: 200 } }} helperText="For rolling calculations" />
                    </Grid>
                    <Grid item xs={12} sm={6} md={3} sx={{display: 'flex', alignItems: 'flex-end'}}>
                        {selectedPairForChart &&
                            <Button variant="contained" onClick={() => handleViewPairDetails(selectedPairForChart)} disabled={isLoadingChart || !chartStartDate || !chartEndDate} fullWidth>
                                {isLoadingChart ? 'Loading Chart...' : `Refresh Chart: ${selectedPairForChart.pair_yx[0]}/${selectedPairForChart.pair_yx[1]}`}
                            </Button>}
                    </Grid>
                </Grid>
            </Paper>

            <Paper sx={{ p: 2, minHeight: 500, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
                {isLoadingChart && <CircularProgress />}
                {errorChart && !isLoadingChart && <Alert severity="error" sx={{width: '100%'}} onClose={() => setErrorChart(null)}>{errorChart}</Alert>}
                {!isLoadingChart && !errorChart && selectedPairForChart && chartPlotData.length > 0 && (
                    <Plot data={chartPlotData} layout={chartPlotLayout} useResizeHandler={true} style={{ width: '100%', height: '500px' }} config={{ responsive: true }}/>
                )}
                {!isLoadingChart && !selectedPairForChart && !errorChart && (
                    <Typography sx={{textAlign: 'center', color: 'text.secondary'}}>Select a pair from the table and set parameters to view historical chart.</Typography>)}
                 {!isLoadingChart && selectedPairForChart && chartPlotData.length === 0 && !errorChart && (
                    <Typography sx={{textAlign: 'center', color: 'text.secondary'}}>No chart data to display. Try adjusting parameters or ensure data is available.</Typography>)}
            </Paper>
        </Container>
    );
};

export default DashboardPage;

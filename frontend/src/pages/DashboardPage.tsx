import React, { useEffect, useState } from 'react';
import {
    Typography, Container, Paper, Box, CircularProgress, Alert,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Button,
    TextField, Grid, Tooltip
} from '@mui/material';
import Plot from 'react-plotly.js'; // For charts
import {
    identifyCointegratedPairs, IdentifiedPairData, IdentifyPairsRequest,
    getPairZScore, PairZScoreRequest, PairZScoreResponse // Import service functions and types
} from '../services/cointegrationService';
import InfoIcon from '@mui/icons-material/Info';


const DashboardPage: React.FC = () => {
    const [identifiedPairs, setIdentifiedPairs] = useState<IdentifiedPairData[]>([]);
    const [isLoadingPairs, setIsLoadingPairs] = useState<boolean>(false);
    const [errorPairs, setErrorPairs] = useState<string | null>(null);
    const [summaryMessage, setSummaryMessage] = useState<string>('');

    const [selectedPairForChart, setSelectedPairForChart] = useState<IdentifiedPairData | null>(null);
    const [chartData, setChartData] = useState<any[]>([]); // For Plotly data
    const [chartLayout, setChartLayout] = useState<any>({}); // For Plotly layout
    const [isLoadingChart, setIsLoadingChart] = useState<boolean>(false);
    const [errorChart, setErrorChart] = useState<string | null>(null);

    // Default tickers to analyze - could be user input in future
    const defaultTickers = ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "ABEV3.SA", "WEGE3.SA"]; // Example B3 tickers
    const [tickersToAnalyze, setTickersToAnalyze] = useState<string>(defaultTickers.join(', '));


    const handleIdentifyPairs = async () => {
        setIsLoadingPairs(true);
        setErrorPairs(null);
        setIdentifiedPairs([]);
        setSummaryMessage('');
        try {
            const params: IdentifyPairsRequest = {
                tickers: tickersToAnalyze.split(',').map(t => t.trim()).filter(t => t),
                // p_value_threshold: 0.05, // Can be made configurable
                // min_observations_for_test: 60,
            };
            if (params.tickers.length < 2) {
                setErrorPairs("Please provide at least two tickers.");
                setIsLoadingPairs(false);
                return;
            }
            const response = await identifyCointegratedPairs(params);
            setIdentifiedPairs(response.pairs);
            setSummaryMessage(response.summary_message);
        } catch (err: any) {
            setErrorPairs(err.message || 'Failed to fetch cointegrated pairs.');
        } finally {
            setIsLoadingPairs(false);
        }
    };

    // Effect to run identification on component mount or when desired
    useEffect(() => {
        // handleIdentifyPairs(); // Optional: run on mount with default tickers
        // For now, let's not auto-run to save API calls during dev
    }, []); // Empty dependency array means it runs once on mount


    const handleViewPairDetails = async (pair: IdentifiedPairData) => {
        setSelectedPairForChart(pair);
        setIsLoadingChart(true);
        setErrorChart(null);
        setChartData([]); // Clear previous chart data

        try {
            const params: PairZScoreRequest = {
                ticker_y: pair.pair_yx[0],
                ticker_x: pair.pair_yx[1],
                // window: 60, // Default or from pair data if available
                use_spread_with_eg_beta: true // Assuming we want spread Z-score
            };
            const zScoreData = await getPairZScore(params);

            if (zScoreData.z_score !== null && zScoreData.z_score !== undefined) {
                setChartData([{
                    y: [zScoreData.z_score],
                    type: 'bar',
                    name: `Current Z-Score (${pair.pair_yx[0]}/${pair.pair_yx[1]})`
                }]);
                setChartLayout({
                    title: `Z-Score for ${pair.pair_yx[0]} / ${pair.pair_yx[1]}`,
                    yaxis: { title: 'Z-Score' }
                });
            } else {
                setChartData([{ y: [0], type: 'bar', name: 'Z-Score N/A'}]); // Show a bar at 0 if N/A
                setChartLayout({ title: `Z-Score data not available for ${pair.pair_yx[0]} / ${pair.pair_yx[1]}` });
            }
            setErrorChart(zScoreData.error || null);

        } catch (err: any) {
            setErrorChart(err.message || `Failed to fetch details for ${pair.pair_yx[0]}/${pair.pair_yx[1]}.`);
            setChartData([]);
        } finally {
            setIsLoadingChart(false);
        }
    };


    return (
        <Container maxWidth="lg">
            <Typography variant="h4" component="h1" gutterBottom sx={{ my: 2 }}>
                Cointegration Dashboard
            </Typography>

            <Paper sx={{ p: 2, mb: 3 }}>
                <Typography variant="h6" gutterBottom>Identify Cointegrated Pairs</Typography>
                <TextField
                    label="Tickers (comma-separated)"
                    value={tickersToAnalyze}
                    onChange={(e) => setTickersToAnalyze(e.target.value)}
                    fullWidth
                    margin="normal"
                    helperText="e.g., PETR4.SA, VALE3.SA, ITUB4.SA"
                />
                <Button variant="contained" onClick={handleIdentifyPairs} disabled={isLoadingPairs} sx={{my:1}}>
                    {isLoadingPairs ? 'Identifying...' : 'Identify Pairs'}
                </Button>
            </Paper>

            {isLoadingPairs && <Box sx={{ display: 'flex', justifyContent: 'center', my: 3 }}><CircularProgress /></Box>}
            {errorPairs && <Alert severity="error" sx={{ my: 2 }}>{errorPairs}</Alert>}
            {summaryMessage && <Alert severity="info" sx={{ my: 2 }}>{summaryMessage}</Alert>}

            <Typography variant="h5" gutterBottom sx={{mt: 3}}>Identified Opportunities</Typography>
            <TableContainer component={Paper} sx={{mb:3}}>
                <Table aria-label="cointegrated pairs table">
                    <TableHead>
                        <TableRow>
                            <TableCell>Pair (Y / X)</TableCell>
                            <TableCell align="right">Hedge Ratio (Beta of X)</TableCell>
                            <TableCell align="right">P-Value (Test)</TableCell>
                            <TableCell align="right">Current Z-Score (Spread)</TableCell>
                            <TableCell align="right">Observations</TableCell>
                            <TableCell align="center">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {identifiedPairs.length === 0 && !isLoadingPairs && (
                            <TableRow>
                                <TableCell colSpan={6} align="center">
                                    No cointegrated pairs found or identified yet.
                                </TableCell>
                            </TableRow>
                        )}
                        {identifiedPairs.map((pair, index) => (
                            <TableRow key={`${pair.pair_yx[0]}-${pair.pair_yx[1]}-${index}`} hover>
                                <TableCell component="th" scope="row">
                                    {pair.pair_yx[0]} / {pair.pair_yx[1]}
                                </TableCell>
                                <TableCell align="right">{pair.hedge_ratio_beta_x?.toFixed(4) || 'N/A'}</TableCell>
                                <TableCell align="right">{pair.p_value.toFixed(4)}</TableCell>
                                <TableCell align="right" sx={{ fontWeight: Math.abs(pair.current_zscore_of_spread || 0) > 1.5 ? 'bold' : 'normal', color: Math.abs(pair.current_zscore_of_spread || 0) > 2 ? 'red' : 'inherit' }}>
                                    {pair.current_zscore_of_spread?.toFixed(2) || 'N/A'}
                                    {Math.abs(pair.current_zscore_of_spread || 0) > 2 &&
                                        <Tooltip title="Potential Entry/Exit Signal (Z-score > |2|)">
                                            <InfoIcon fontSize="small" sx={{verticalAlign: 'middle', ml:0.5, cursor: 'help'}} color="error"/>
                                        </Tooltip>
                                    }
                                </TableCell>
                                <TableCell align="right">{pair.n_observations_in_test}</TableCell>
                                <TableCell align="center">
                                    <Button size="small" onClick={() => handleViewPairDetails(pair)} variant="outlined">View Details</Button>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            <Typography variant="h5" gutterBottom sx={{mt:3}}>Pair Details & Chart</Typography>
            <Paper sx={{ p: 2, minHeight: 400, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
                {isLoadingChart && <CircularProgress />}
                {errorChart && !isLoadingChart && <Alert severity="error" sx={{width: '100%'}}>{errorChart}</Alert>}
                {!isLoadingChart && !errorChart && selectedPairForChart && chartData.length > 0 && (
                    <Plot
                        data={chartData}
                        layout={{ ...chartLayout, autosize: true, height: 360 }} // Fixed height for plot area
                        useResizeHandler={true}
                        style={{ width: '100%', height: '100%' }}
                        config={{ responsive: true }}
                    />
                )}
                {!isLoadingChart && !selectedPairForChart && !errorChart &&(
                    <Typography sx={{textAlign: 'center', color: 'text.secondary'}}>
                        Select a pair from the table above to view details and chart.
                    </Typography>
                )}
                 {!isLoadingChart && selectedPairForChart && chartData.length === 0 && !errorChart && (
                    <Typography sx={{textAlign: 'center', color: 'text.secondary'}}>
                        No chart data to display for {selectedPairForChart.pair_yx[0]}/{selectedPairForChart.pair_yx[1]}. This might be due to an error fetching Z-Score or Z-Score being null.
                    </Typography>
                )}
            </Paper>
        </Container>
    );
};

export default DashboardPage;

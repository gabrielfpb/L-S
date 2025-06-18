import React, { useEffect, useState, useCallback } from 'react';
import {
    Typography, Container, Paper, Box, CircularProgress, Alert, Button,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, IconButton,
    Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, TextField, Grid, Tooltip
} from '@mui/material';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import EditIcon from '@mui/icons-material/Edit'; // For future edit functionality
import HighlightOffIcon from '@mui/icons-material/HighlightOff'; // For "Close Trade"
import { useAuth } from '../contexts/AuthContext'; // To get current user for filtering if needed
import * as tradeService from '../services/tradeService'; // Import trade service

const TradeManagementPage: React.FC = () => {
    const [trades, setTrades] = useState<tradeService.Trade[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const { user, isAuthenticated } = useAuth(); // Get authenticated user and auth status

    const [openCreateDialog, setOpenCreateDialog] = useState(false);
    const [newTradeData, setNewTradeData] = useState<tradeService.TradeCreateData>({
        asset1_ticker: '', asset2_ticker: '', quantity_asset1: 0, quantity_asset2: 0,
        trade_type: 'LONG_SHORT_ENTRY', status: 'OPEN', // Sensible defaults
    });

    const [openCloseTradeDialog, setOpenCloseTradeDialog] = useState(false);
    const [tradeToClose, setTradeToClose] = useState<tradeService.Trade | null>(null);
    const [closeTradeDetails, setCloseTradeDetails] = useState({
        exit_price_asset1: '', exit_price_asset2: '', notes: ''
    });


    const fetchTrades = useCallback(async () => {
        if (!isAuthenticated || !user) { // Check if user is authenticated and user object exists
            setTrades([]); // Clear trades if not authenticated
            return;
        }
        setIsLoading(true);
        setError(null);
        try {
            // Backend handles filtering by authenticated user or allows admin override
            const fetchedTrades = await tradeService.getTrades();
            setTrades(fetchedTrades);
        } catch (err: any) {
            setError(err.message || 'Failed to fetch trades.');
        } finally {
            setIsLoading(false);
        }
    }, [isAuthenticated, user]); // Depend on isAuthenticated and user

    useEffect(() => {
        fetchTrades();
    }, [fetchTrades]);

    const handleCreateDialogOpen = () => {
        setError(null); // Clear previous dialog errors
        setNewTradeData({
            asset1_ticker: '', asset2_ticker: '', quantity_asset1: 0, quantity_asset2: 0,
            trade_type: 'LONG_SHORT_ENTRY', status: 'OPEN', entry_price_asset1: null, entry_price_asset2: null,
            entry_zscore: null, notes: '', cointegrated_pair_id: null, stop_loss_level: null, take_profit_level: null
        }); // Reset form
        setOpenCreateDialog(true);
    };
    const handleCreateDialogClose = () => setOpenCreateDialog(false);

    const handleNewTradeChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        const { name, value } = event.target;
        const isNumberField = ['quantity_asset1', 'quantity_asset2', 'entry_price_asset1', 'entry_price_asset2', 'entry_zscore', 'cointegrated_pair_id', 'stop_loss_level', 'take_profit_level'].includes(name);

        setNewTradeData(prev => ({
            ...prev,
            [name]: isNumberField ? (value === '' ? null : parseFloat(value)) : value
        }));
    };


    const handleCreateTrade = async () => {
        setError(null); // Clear previous main page error
        try {
            if (!newTradeData.asset1_ticker || !newTradeData.asset2_ticker || newTradeData.quantity_asset1 === 0 || newTradeData.quantity_asset2 === 0) {
                // This error should ideally be shown in the dialog, not on the main page
                // For simplicity, we'll use the main error state for now.
                setError("Asset tickers and non-zero quantities are required for assets 1 & 2.");
                return;
            }
            await tradeService.createTrade(newTradeData);
            handleCreateDialogClose();
            fetchTrades();
        } catch (err: any) {
            setError(err.message || 'Failed to create trade.');
        }
    };

    const handleCloseTradeDialogOpen = (trade: tradeService.Trade) => {
        setError(null); // Clear previous dialog errors
        setTradeToClose(trade);
        setCloseTradeDetails({ exit_price_asset1: '', exit_price_asset2: '', notes: `Closing trade for ${trade.asset1_ticker}/${trade.asset2_ticker}` });
        setOpenCloseTradeDialog(true);
    };
    const handleCloseTradeDialogClose = () => {
        setOpenCloseTradeDialog(false);
        setTradeToClose(null);
    };
    const handleCloseTradeDetailsChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        const { name, value } = event.target;
        setCloseTradeDetails(prev => ({ ...prev, [name]: value }));
    };

    const handleConfirmCloseTrade = async () => {
        if (!tradeToClose) return;
        setError(null); // Clear previous main page error
        try {
            const updateData: tradeService.TradeUpdateData = {
                status: "CLOSED",
                exit_datetime: new Date().toISOString(),
                exit_price_asset1: closeTradeDetails.exit_price_asset1 !== '' ? parseFloat(closeTradeDetails.exit_price_asset1) : null,
                exit_price_asset2: closeTradeDetails.exit_price_asset2 !== '' ? parseFloat(closeTradeDetails.exit_price_asset2) : null,
                notes: closeTradeDetails.notes,
            };
            await tradeService.updateTrade(tradeToClose.id, updateData);
            handleCloseTradeDialogClose();
            fetchTrades();
        } catch (err: any) {
            setError(err.message || "Failed to close trade.");
        }
    };

    const formatDate = (dateString?: string | null) => {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleString();
    };

    if (!isAuthenticated) { // Optional: Show a message if user is not authenticated
        return (
            <Container>
                <Alert severity="info" sx={{mt: 3}}>Please login to manage trades.</Alert>
            </Container>
        );
    }

    return (
        <Container maxWidth="xl">
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', my: 2 }}>
                <Typography variant="h4" component="h1" gutterBottom>
                    Trade Management
                </Typography>
                <Button variant="contained" startIcon={<AddCircleOutlineIcon />} onClick={handleCreateDialogOpen}>
                    New Trade
                </Button>
            </Box>

            {isLoading && <Box sx={{ display: 'flex', justifyContent: 'center', my: 3 }}><CircularProgress /></Box>}
            {!isLoading && error && <Alert severity="error" sx={{ my: 2 }} onClose={() => setError(null)}>{error}</Alert>}

            <TableContainer component={Paper}>
                <Table aria-label="trades table" size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>ID</TableCell>
                            <TableCell>Pair (A1/A2)</TableCell>
                            <TableCell>Type</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell>Entry Time</TableCell>
                            <TableCell align="right">Qty A1</TableCell>
                            <TableCell align="right">Entry P1</TableCell>
                            <TableCell align="right">Qty A2</TableCell>
                            <TableCell align="right">Entry P2</TableCell>
                            <TableCell align="right">Entry Z</TableCell>
                            <TableCell>Exit Time</TableCell>
                            <TableCell align="right">P&L</TableCell>
                            <TableCell align="center">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {trades.length === 0 && !isLoading && (
                            <TableRow><TableCell colSpan={13} align="center">No trades found.</TableCell></TableRow>
                        )}
                        {trades.map((trade) => (
                            <TableRow key={trade.id} hover>
                                <TableCell>{trade.id}</TableCell>
                                <TableCell>{trade.asset1?.ticker || trade.asset1_ticker}/{trade.asset2?.ticker || trade.asset2_ticker}</TableCell>
                                <TableCell>{trade.trade_type}</TableCell>
                                <TableCell>{trade.status}</TableCell>
                                <TableCell>{formatDate(trade.entry_datetime)}</TableCell>
                                <TableCell align="right">{trade.quantity_asset1?.toFixed(2)}</TableCell>
                                <TableCell align="right">{trade.entry_price_asset1?.toFixed(2) || 'N/A'}</TableCell>
                                <TableCell align="right">{trade.quantity_asset2?.toFixed(2)}</TableCell>
                                <TableCell align="right">{trade.entry_price_asset2?.toFixed(2) || 'N/A'}</TableCell>
                                <TableCell align="right">{trade.entry_zscore?.toFixed(2) || 'N/A'}</TableCell>
                                <TableCell>{formatDate(trade.exit_datetime)}</TableCell>
                                <TableCell align="right" sx={{color: (trade.realized_pnl ?? 0) < 0 ? 'error.main' : (trade.realized_pnl ?? 0) > 0 ? 'success.main' : 'text.primary'}}>
                                    {trade.realized_pnl?.toFixed(2) ?? (trade.status === "CLOSED" ? '0.00' : 'N/A')}
                                </TableCell>
                                <TableCell align="center">
                                    {trade.status === "OPEN" && (
                                        <Tooltip title="Close Trade">
                                            <IconButton size="small" onClick={() => handleCloseTradeDialogOpen(trade)} color="warning">
                                                <HighlightOffIcon />
                                            </IconButton>
                                        </Tooltip>
                                    )}
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            <Dialog open={openCreateDialog} onClose={handleCreateDialogClose} maxWidth="sm" fullWidth>
                <DialogTitle>Create New Trade</DialogTitle>
                <DialogContent>
                    <DialogContentText sx={{mb:1}}>
                        Enter details for the new trade. Asset tickers must exist or be creatable by the backend.
                    </DialogContentText>
                    {/* Dialog-specific error display could be added here if main 'error' state is too broad */}
                    <Grid container spacing={2} sx={{mt:1}}>
                        <Grid item xs={12} sm={6}><TextField name="asset1_ticker" label="Asset 1 Ticker (e.g., Long)" value={newTradeData.asset1_ticker} onChange={handleNewTradeChange} fullWidth /></Grid>
                        <Grid item xs={12} sm={6}><TextField name="asset2_ticker" label="Asset 2 Ticker (e.g., Short)" value={newTradeData.asset2_ticker} onChange={handleNewTradeChange} fullWidth /></Grid>
                        <Grid item xs={12} sm={6}><TextField name="quantity_asset1" label="Quantity Asset 1" type="number" value={newTradeData.quantity_asset1} onChange={handleNewTradeChange} fullWidth InputLabelProps={{ shrink: true }} /></Grid>
                        <Grid item xs={12} sm={6}><TextField name="quantity_asset2" label="Quantity Asset 2" type="number" value={newTradeData.quantity_asset2} onChange={handleNewTradeChange} fullWidth InputLabelProps={{ shrink: true }} /></Grid>
                        <Grid item xs={12} sm={6}><TextField name="entry_price_asset1" label="Entry Price A1 (Opt.)" type="number" value={newTradeData.entry_price_asset1 ?? ''} onChange={handleNewTradeChange} fullWidth InputLabelProps={{ shrink: true }} /></Grid>
                        <Grid item xs={12} sm={6}><TextField name="entry_price_asset2" label="Entry Price A2 (Opt.)" type="number" value={newTradeData.entry_price_asset2 ?? ''} onChange={handleNewTradeChange} fullWidth InputLabelProps={{ shrink: true }} /></Grid>
                        <Grid item xs={12} sm={6}><TextField name="entry_zscore" label="Entry Z-Score (Opt.)" type="number" value={newTradeData.entry_zscore ?? ''} onChange={handleNewTradeChange} fullWidth InputLabelProps={{ shrink: true }} /></Grid>
                        <Grid item xs={12} sm={6}><TextField name="trade_type" label="Trade Type" value={newTradeData.trade_type} onChange={handleNewTradeChange} fullWidth helperText="e.g. LONG_SHORT_ENTRY" InputLabelProps={{ shrink: true }}/></Grid>
                        <Grid item xs={12}><TextField name="notes" label="Notes (Optional)" value={newTradeData.notes ?? ''} onChange={handleNewTradeChange} fullWidth multiline rows={2} InputLabelProps={{ shrink: true }}/></Grid>
                    </Grid>
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleCreateDialogClose}>Cancel</Button>
                    <Button onClick={handleCreateTrade} variant="contained">Create Trade</Button>
                </DialogActions>
            </Dialog>

            {tradeToClose && (
                <Dialog open={openCloseTradeDialog} onClose={handleCloseTradeDialogClose} maxWidth="sm" fullWidth>
                    <DialogTitle>Close Trade: {tradeToClose.asset1?.ticker || tradeToClose.asset1_ticker}/{tradeToClose.asset2?.ticker || tradeToClose.asset2_ticker}</DialogTitle>
                    <DialogContent>
                         <DialogContentText sx={{mb:1}}>
                            Enter exit details to close this trade.
                        </DialogContentText>
                        <Grid container spacing={2} sx={{mt:1}}>
                            <Grid item xs={12} sm={6}><TextField name="exit_price_asset1" label="Exit Price A1" type="number" value={closeTradeDetails.exit_price_asset1} onChange={handleCloseTradeDetailsChange} fullWidth InputLabelProps={{ shrink: true }} /></Grid>
                            <Grid item xs={12} sm={6}><TextField name="exit_price_asset2" label="Exit Price A2" type="number" value={closeTradeDetails.exit_price_asset2} onChange={handleCloseTradeDetailsChange} fullWidth InputLabelProps={{ shrink: true }} /></Grid>
                            <Grid item xs={12}><TextField name="notes" label="Exit Notes (Optional)" value={closeTradeDetails.notes} onChange={handleCloseTradeDetailsChange} fullWidth multiline rows={2} InputLabelProps={{ shrink: true }}/></Grid>
                        </Grid>
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={handleCloseTradeDialogClose}>Cancel</Button>
                        <Button onClick={handleConfirmCloseTrade} variant="contained" color="warning">Confirm Close</Button>
                    </DialogActions>
                </Dialog>
            )}
        </Container>
    );
};

export default TradeManagementPage;

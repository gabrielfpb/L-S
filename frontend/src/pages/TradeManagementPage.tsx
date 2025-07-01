import React, { useEffect, useState, useCallback } from 'react';
import {
    Typography, Container, Paper, Box, CircularProgress, Alert, Button,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, IconButton,
    Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, TextField, Grid, Tooltip,
    TableSortLabel, TablePagination // Added for sorting and pagination
} from '@mui/material';
import { visuallyHidden } from '@mui/utils'; // For screen reader text with TableSortLabel
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import EditIcon from '@mui/icons-material/Edit';
import HighlightOffIcon from '@mui/icons-material/HighlightOff';
import { useAuth } from '../contexts/AuthContext'; // To get current user for filtering if needed
import * as tradeService from '../services/tradeService'; // Import trade service

const TradeManagementPage: React.FC = () => {
    const [trades, setTrades] = useState<tradeService.Trade[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string|null>(null); // Added for main page success messages
    const { user, isAuthenticated } = useAuth();

    // Sorting state
    type Order = 'asc' | 'desc';
    type TradeSortKeys = keyof tradeService.Trade | 'pair';
    const [order, setOrder] = useState<Order>('desc');
    const [orderBy, setOrderBy] = useState<TradeSortKeys>('entry_datetime');

    // Pagination state
    const [page, setPage] = useState(0);
    const [rowsPerPage, setRowsPerPage] = useState(10);
    const { user, isAuthenticated } = useAuth();

    // Define headCells for Trade Table
    interface HeadCell { id: TradeSortKeys; label: string; numeric: boolean; disablePadding?: boolean; }
    const headCells: readonly HeadCell[] = [
        { id: 'id', numeric: true, label: 'ID' },
        { id: 'pair', numeric: false, label: 'Pair (A1/A2)' },
        { id: 'trade_type', numeric: false, label: 'Type' },
        { id: 'status', numeric: false, label: 'Status' },
        { id: 'entry_datetime', numeric: false, label: 'Entry Time' },
        { id: 'quantity_asset1', numeric: true, label: 'Qty A1' },
        { id: 'entry_price_asset1', numeric: true, label: 'Entry P1' },
        { id: 'quantity_asset2', numeric: true, label: 'Qty A2' },
        { id: 'entry_price_asset2', numeric: true, label: 'Entry P2' },
        { id: 'entry_zscore', numeric: true, label: 'Entry Z' },
        { id: 'exit_datetime', numeric: false, label: 'Exit Time' },
        { id: 'realized_pnl', numeric: true, label: 'P&L' },
        { id: 'actions', numeric: false, label: 'Actions', disablePadding: true },
    ];

    const [openCreateDialog, setOpenCreateDialog] = useState(false);
    const [newTradeData, setNewTradeData] = useState<tradeService.TradeCreateData>({
        asset1_ticker: '', asset2_ticker: '', quantity_asset1: 0, quantity_asset2: 0,
        trade_type: 'LONG_SHORT_ENTRY', status: 'OPEN', // Sensible defaults
    });
    const [isCreatingTrade, setIsCreatingTrade] = useState(false); // Specific loading state for dialog
    const [createTradeError, setCreateTradeError] = useState<string|null>(null); // Specific error state for dialog


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
        setCreateTradeError(null); // Clear previous dialog error
        setNewTradeData({
            asset1_ticker: '', asset2_ticker: '', quantity_asset1: 0, quantity_asset2: 0,
            trade_type: 'LONG_SHORT_ENTRY', status: 'OPEN', entry_price_asset1: null, entry_price_asset2: null,
            entry_zscore: null, notes: '', cointegrated_pair_id: null, stop_loss_level: null, take_profit_level: null
        }); // Reset form
        setOpenCreateDialog(true);
    };
    const handleCreateDialogClose = () => {
        setOpenCreateDialog(false);
        setCreateTradeError(null);
    };

    const handleRequestSort = (property: TradeSortKeys) => {
        const isAsc = orderBy === property && order === 'asc';
        setOrder(isAsc ? 'desc' : 'asc');
        setOrderBy(property);
    };

    const handleChangePage = (event: unknown, newPage: number) => setPage(newPage);
    const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
        setRowsPerPage(parseInt(event.target.value, 10));
        setPage(0);
    };

    // Client-side sorting and pagination logic
    function descendingComparator<T>(a: T, b: T, orderByProperty: keyof T) {
        if (b[orderByProperty] == null && a[orderByProperty] != null) return -1;
        if (a[orderByProperty] == null && b[orderByProperty] != null) return 1;
        if (b[orderByProperty] == null && a[orderByProperty] == null) return 0;

        if (b[orderByProperty] < a[orderByProperty]) return -1;
        if (b[orderByProperty] > a[orderByProperty]) return 1;
        return 0;
    }

    function getComparator<Key extends keyof any>(
        currentOrder: Order,
        orderByProperty: Key,
    ): (a: { [key in Key]?: any }, b: { [key in Key]?: any }) => number {
        return currentOrder === 'desc'
            ? (a, b) => descendingComparator(a, b, orderByProperty)
            : (a, b) => -descendingComparator(a, b, orderByProperty);
    }

    function stableSort<T>(array: readonly T[], comparator: (a: T, b: T) => number) {
        const stabilizedThis = array.map((el, index) => [el, index] as [T, number]);
        stabilizedThis.sort((a, b) => {
            const orderResult = comparator(a[0], b[0]);
            if (orderResult !== 0) return orderResult;
            return a[1] - b[1];
        });
        return stabilizedThis.map((el) => el[0]);
    }

    const sortedTrades = React.useMemo(() => {
        const sortableTrades = trades.map(t => ({
            ...t,
            pair: `${t.asset1?.ticker || t.asset1_ticker}/${t.asset2?.ticker || t.asset2_ticker}`
        }));
        return stableSort(sortableTrades, getComparator(order, orderBy as any)) // Use 'as any' for orderBy if complex type
            .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);
    }, [trades, order, orderBy, page, rowsPerPage]);


    const handleNewTradeChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        const { name, value } = event.target;
        const isNumberField = ['quantity_asset1', 'quantity_asset2', 'entry_price_asset1', 'entry_price_asset2', 'entry_zscore', 'cointegrated_pair_id', 'stop_loss_level', 'take_profit_level'].includes(name);

        setNewTradeData(prev => ({
            ...prev,
            [name]: isNumberField ? (value === '' ? null : parseFloat(value)) : value
        }));
    };


    const handleCreateTrade = async () => {
        setCreateTradeError(null);
        setIsCreatingTrade(true);
        try {
            if (!newTradeData.asset1_ticker || !newTradeData.asset2_ticker ||
                newTradeData.quantity_asset1 === 0 || newTradeData.quantity_asset2 === 0) {
                setCreateTradeError("Asset tickers and non-zero quantities are required for assets 1 & 2.");
                setIsCreatingTrade(false);
                return;
            }
            // Example: Prevent negative quantities if your logic implies direction by asset roles
            // This depends on how your backend/model handles quantities (e.g. if negative means short)
            // For now, assuming positive quantities are expected by the form for simplicity of example.
            if (newTradeData.quantity_asset1 <= 0 || newTradeData.quantity_asset2 <= 0) {
                 setCreateTradeError("Quantities must be positive numbers.");
                 setIsCreatingTrade(false);
                 return;
            }

            await tradeService.createTrade(newTradeData);
            handleCreateDialogClose();
            fetchTrades();
            setSuccessMessage("Trade created successfully!"); // Use main page success for this
        } catch (err: any) {
            setCreateTradeError(err.message || 'Failed to create trade.');
        } finally {
            setIsCreatingTrade(false);
        }
    };

    const handleCloseTradeDialogOpen = (trade: tradeService.Trade) => {
        // setError(null); // Main page error, consider if dialog needs its own error state too
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
                            {headCells.map((headCell) => (
                                <TableCell key={headCell.id} align={headCell.numeric ? 'right' : 'left'}
                                           padding={headCell.disablePadding ? 'none' : 'normal'}
                                           sortDirection={orderBy === headCell.id ? order : false}>
                                    <TableSortLabel active={orderBy === headCell.id} direction={orderBy === headCell.id ? order : 'asc'}
                                                    onClick={() => handleRequestSort(headCell.id as any)}>
                                        {headCell.label}
                                        {orderBy === headCell.id ? (<Box component="span" sx={visuallyHidden}>
                                            {order === 'desc' ? 'sorted descending' : 'sorted ascending'}
                                        </Box>) : null}
                                    </TableSortLabel>
                                </TableCell>
                            ))}
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {sortedTrades.length === 0 && !isLoading && ( // Use sortedTrades here
                            <TableRow><TableCell colSpan={headCells.length} align="center">No trades found.</TableCell></TableRow>
                        )}
                        {sortedTrades.map((trade) => ( // Use sortedTrades here
                            <TableRow key={trade.id} hover>
                                <TableCell>{trade.id}</TableCell>
                                <TableCell>{trade.pair}</TableCell> {/* Display the computed pair string */}
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
            <TablePagination
                rowsPerPageOptions={[5, 10, 25, 50]}
                component="div"
                count={trades.length} // Total count of trades (before client-side slicing)
                rowsPerPage={rowsPerPage}
                page={page}
                onPageChange={handleChangePage}
                onRowsPerPageChange={handleChangeRowsPerPage}
            />

            <Dialog open={openCreateDialog} onClose={handleCreateDialogClose} maxWidth="sm" fullWidth>
                <DialogTitle>Create New Trade</DialogTitle>
                <DialogContent>
                    <DialogContentText sx={{mb:1}}>
                        Enter details for the new trade. Asset tickers must exist or be creatable by the backend.
                    </DialogContentText>
                    {createTradeError && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setCreateTradeError(null)}>{createTradeError}</Alert>}
                    <Grid container spacing={2} sx={{mt:1}}>
                        <Grid item xs={12} sm={6}><TextField name="asset1_ticker" label="Asset 1 Ticker (e.g., Long)" value={newTradeData.asset1_ticker} onChange={handleNewTradeChange} fullWidth disabled={isCreatingTrade} /></Grid>
                        <Grid item xs={12} sm={6}><TextField name="asset2_ticker" label="Asset 2 Ticker (e.g., Short)" value={newTradeData.asset2_ticker} onChange={handleNewTradeChange} fullWidth disabled={isCreatingTrade} /></Grid>
                        <Grid item xs={12} sm={6}><TextField name="quantity_asset1" label="Quantity Asset 1" type="number" value={newTradeData.quantity_asset1} onChange={handleNewTradeChange} fullWidth InputLabelProps={{ shrink: true }} disabled={isCreatingTrade} /></Grid>
                        <Grid item xs={12} sm={6}><TextField name="quantity_asset2" label="Quantity Asset 2" type="number" value={newTradeData.quantity_asset2} onChange={handleNewTradeChange} fullWidth InputLabelProps={{ shrink: true }} disabled={isCreatingTrade} /></Grid>
                        <Grid item xs={12} sm={6}><TextField name="entry_price_asset1" label="Entry Price A1 (Opt.)" type="number" value={newTradeData.entry_price_asset1 ?? ''} onChange={handleNewTradeChange} fullWidth InputLabelProps={{ shrink: true }} disabled={isCreatingTrade} /></Grid>
                        <Grid item xs={12} sm={6}><TextField name="entry_price_asset2" label="Entry Price A2 (Opt.)" type="number" value={newTradeData.entry_price_asset2 ?? ''} onChange={handleNewTradeChange} fullWidth InputLabelProps={{ shrink: true }} disabled={isCreatingTrade} /></Grid>
                        <Grid item xs={12} sm={6}><TextField name="entry_zscore" label="Entry Z-Score (Opt.)" type="number" value={newTradeData.entry_zscore ?? ''} onChange={handleNewTradeChange} fullWidth InputLabelProps={{ shrink: true }} disabled={isCreatingTrade} /></Grid>
                        <Grid item xs={12} sm={6}><TextField name="trade_type" label="Trade Type" value={newTradeData.trade_type} onChange={handleNewTradeChange} fullWidth helperText="e.g. LONG_SHORT_ENTRY" InputLabelProps={{ shrink: true }} disabled={isCreatingTrade}/></Grid>
                        <Grid item xs={12}><TextField name="notes" label="Notes (Optional)" value={newTradeData.notes ?? ''} onChange={handleNewTradeChange} fullWidth multiline rows={2} InputLabelProps={{ shrink: true }} disabled={isCreatingTrade}/></Grid>
                    </Grid>
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleCreateDialogClose} disabled={isCreatingTrade}>Cancel</Button>
                    <Button onClick={handleCreateTrade} variant="contained" disabled={isCreatingTrade}>
                        {isCreatingTrade ? <CircularProgress size={24} /> : "Create Trade"}
                    </Button>
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

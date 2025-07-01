import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterMoment } from '@mui/x-date-pickers/AdapterMoment';
import '@testing-library/jest-dom';

import ReportsPage from './ReportsPage';
import * as reportService from '../services/reportService';
import { AuthContext, User } from '../contexts/AuthContext';

// Mock Plotly component for equity curve chart
jest.mock('react-plotly.js', () => ({
    __esModule: true,
    default: jest.fn(() => <div data-testid="plotly-equity-chart-mock"></div>),
}));

const theme = createTheme();
const mockUser: User = {id:1, username:'test', email:'test@test.com', is_active:true, is_superuser: false};
const mockAuthContextValue = {
    isAuthenticated: true, user: mockUser,
    token: 'fake-token', login: jest.fn(), logout: jest.fn(), isLoading: false, error: null
};

// Helper to wrap component in necessary providers
const renderReportsPage = () => {
    return render(
        <AuthContext.Provider value={mockAuthContextValue}>
            <ThemeProvider theme={theme}>
                <LocalizationProvider dateAdapter={AdapterMoment}>
                    <BrowserRouter><ReportsPage /></BrowserRouter>
                </LocalizationProvider>
            </ThemeProvider>
        </AuthContext.Provider>
    );
};

describe('ReportsPage - Backtest Form and Results', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        // Mock getGeneratedReports to return an empty list initially
        jest.spyOn(reportService, 'getGeneratedReports').mockResolvedValue([]);
    });

    test('renders new backtest parameter fields in the form', () => {
        renderReportsPage();

        expect(screen.getByLabelText(/Strategy Name/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Tickers for Pair \(Y,X\)/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Initial Capital/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Z Window/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Entry Z/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Exit Z/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Report Name \(Optional\)/i)).toBeInTheDocument();
    });

    test('submits backtest request with new parameters', async () => {
        const mockRequestBacktest = jest.spyOn(reportService, 'requestBacktestReportGeneration')
                                      .mockResolvedValue({ task_id: "task-123", message: "Backtest queued", report_id: 1, status_check_url: "" });
        renderReportsPage();

        fireEvent.change(screen.getByLabelText(/Tickers for Pair \(Y,X\)/i), { target: { value: 'STOCKA.SA,STOCKB.SA' } });
        fireEvent.change(screen.getByLabelText(/Z Window/i), { target: { value: '25' } });
        fireEvent.change(screen.getByLabelText(/Entry Z/i), { target: { value: '2.2' } });
        fireEvent.change(screen.getByLabelText(/Exit Z/i), { target: { value: '0.3' } });
        fireEvent.change(screen.getByLabelText(/Report Name \(Optional\)/i), { target: { value: 'My Test Backtest' } });


        fireEvent.click(screen.getByRole('button', { name: /Run Backtest/i }));

        await waitFor(() => expect(mockRequestBacktest).toHaveBeenCalledWith(expect.objectContaining({
            tickers: ["STOCKA.SA", "STOCKB.SA"],
            z_score_window: 25,
            entry_z_threshold: 2.2,
            exit_z_threshold: 0.3,
            report_name: 'My Test Backtest'
        })));
    });

    test('displays backtest results including equity curve when view details is clicked', async () => {
        const mockReport: reportService.Report = {
            id: "rep1", report_type: "BACKTEST", generated_at: new Date().toISOString(), status: "COMPLETED",
            report_name: "Detailed Test Backtest",
            parameters: { tickers: ["Y", "X"], start_date: "2023-01-01", end_date: "2023-02-01", strategy_name: "zscore_v1"},
            summary_data: { // Ensure this matches structure from backend generate_backtest_data
                total_pnl_on_spread_units: 120.50,
                number_of_trades: 5,
                win_rate: 0.6,
                sharpe_ratio_approx: 1.25,
                equity_curve_dates: [new Date().toISOString(), new Date(Date.now() + 86400000).toISOString()], // Two dates
                equity_curve_values: [1000.0, 1120.50] // Corresponding values
            }
        };
        // Override the initial empty mock for this specific test
        jest.spyOn(reportService, 'getGeneratedReports').mockResolvedValue([mockReport]);

        renderReportsPage();

        // Wait for table to render (due to async fetchReports) and find the view results button
        const viewResultsButton = await screen.findByRole('button', { name: /view results/i });
        fireEvent.click(viewResultsButton);

        // Dialog with details should appear
        await waitFor(() => {
            expect(screen.getByText(/Report Details: Detailed Test Backtest/i)).toBeInTheDocument();
            // Check for a key metric
            expect(screen.getByText(/Total Pnl On Spread Units:/i)).toBeInTheDocument();
            expect(screen.getByText("120.50")).toBeInTheDocument();
            // Check if Plotly mock for equity curve was rendered
            expect(screen.getByTestId('plotly-equity-chart-mock')).toBeInTheDocument();
        });
    });
});
```

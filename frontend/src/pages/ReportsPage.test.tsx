import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterMoment } from '@mui/x-date-pickers/AdapterMoment';
import '@testing-library/jest-dom';

import ReportsPage from './ReportsPage';
import * as reportService from '../services/reportService';
import { AuthContext, User } from '../contexts/AuthContext';
// Import NotificationContext to provide it, useNotifier will be mocked for these specific tests
import { NotificationContext } from '../contexts/NotificationContext';

jest.useFakeTimers(); // Use Jest's fake timers for setInterval

// Mock Plotly component
jest.mock('react-plotly.js', () => ({
    __esModule: true,
    default: jest.fn(() => <div data-testid="plotly-equity-chart-mock"></div>),
}));

const theme = createTheme();
const mockUser: User = {id:1, username:'testUser', email:'test@example.com', is_active:true, is_superuser: false};
const mockAuthContextValue = {
    isAuthenticated: true, user: mockUser,
    token: 'fake-token', login: jest.fn(), logout: jest.fn(), isLoading: false, error: null
};
const mockShowNotification = jest.fn();


// Helper to wrap component in necessary providers
const renderReportsPage = () => {
    return render(
        <AuthContext.Provider value={mockAuthContextValue}>
            <NotificationContext.Provider value={{ showNotification: mockShowNotification }}>
                <ThemeProvider theme={theme}>
                    <LocalizationProvider dateAdapter={AdapterMoment}>
                        <BrowserRouter><ReportsPage /></BrowserRouter>
                    </LocalizationProvider>
                </ThemeProvider>
            </NotificationContext.Provider>
        </AuthContext.Provider>
    );
};


describe('ReportsPage - Task Polling and General Rendering', () => {
    let mockGetReportTaskStatus: jest.SpyInstance;
    let mockRequestBacktestReport: jest.SpyInstance;
    let mockGetGeneratedReports: jest.SpyInstance;

    beforeEach(() => {
        jest.clearAllMocks();

        mockGetGeneratedReports = jest.spyOn(reportService, 'getGeneratedReports').mockResolvedValue([]);
        mockGetReportTaskStatus = jest.spyOn(reportService, 'getReportTaskStatus');
        mockRequestBacktestReport = jest.spyOn(reportService, 'requestBacktestReportGeneration');
    });

    afterEach(() => {
        jest.clearAllTimers();
    });

    // Test from previous subtask plan (adapted)
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

    // Test from previous subtask plan (adapted)
    test('submits backtest request with new parameters', async () => {
        mockRequestBacktestReport.mockResolvedValue({ task_id: "task-456", message: "queued", report_id: 2 } as any);
        renderReportsPage();

        fireEvent.change(screen.getByLabelText(/Tickers for Pair \(Y,X\)/i), { target: { value: 'BTC-USD,ETH-USD' } });
        fireEvent.change(screen.getByLabelText(/Z Window/i), { target: { value: '25' } });
        fireEvent.click(screen.getByRole('button', { name: /Run Backtest/i }));

        await waitFor(() => expect(mockRequestBacktest).toHaveBeenCalledWith(expect.objectContaining({
            tickers: ["BTC-USD", "ETH-USD"],
            z_score_window: 25
        })));
    });

    test('initiates polling when a report task starts and updates status, then stops polling on completion', async () => {
        mockRequestBacktestReport.mockResolvedValue({
            task_id: "task123",
            report_id: 1,
            message: "Backtest queued",
            status: "PENDING"
        });

        mockGetReportTaskStatus
            .mockResolvedValueOnce({ task_id: "task123", status: "STARTED", result: null })
            .mockResolvedValueOnce({ task_id: "task123", status: "PROCESSING", result: null })
            .mockResolvedValueOnce({ task_id: "task123", status: "SUCCESS", result: { final_data: "done" } });

        const finalCompletedReport: reportService.Report = {
            id: "1",
            report_type: "BACKTEST", generated_at: new Date().toISOString(),
            status: "COMPLETED", report_name: "Backtest: TCK1.SA/TCK2.SA", // Example name
            parameters: {}, summary_data: { final_data: "done" }
        };
        // fetchReports is called after task completion. 1st call on mount, 2nd on completion.
        mockGetGeneratedReports.mockResolvedValueOnce([]).mockResolvedValueOnce([finalCompletedReport]);

        renderReportsPage();

        fireEvent.change(screen.getByLabelText(/Tickers for Pair \(Y,X\)/i), { target: { value: 'TCK1.SA,TCK2.SA' } });
        fireEvent.click(screen.getByRole('button', { name: /Run Backtest/i }));

        await waitFor(() => expect(mockRequestBacktest).toHaveBeenCalled());

        // Check for initial optimistic update (PENDING for the new report)
        // The report name is dynamically generated, so we look for status.
        // Since there might be other "PENDING" texts if other tests run, be more specific or ensure clean state.
        // Here, we expect the table to eventually show the new report.
        await screen.findByText(/PENDING/i, {}, {timeout: 1000});


        act(() => { jest.advanceTimersByTime(POLLING_INTERVAL); });
        await waitFor(() => expect(mockGetReportTaskStatus).toHaveBeenCalledWith("task123"));
        await screen.findByText(/STARTED/i, {}, {timeout: 1000});


        act(() => { jest.advanceTimersByTime(POLLING_INTERVAL); });
        await waitFor(() => expect(mockGetReportTaskStatus).toHaveBeenCalledTimes(2));
        await screen.findByText(/PROCESSING/i, {}, {timeout: 1000});


        act(() => { jest.advanceTimersByTime(POLLING_INTERVAL); });
        await waitFor(() => expect(mockGetReportTaskStatus).toHaveBeenCalledTimes(3));

        await waitFor(() => expect(mockGetGeneratedReports).toHaveBeenCalledTimes(2));

        expect(await screen.findByText("COMPLETED")).toBeInTheDocument();
        expect(await screen.findByText(finalCompletedReport.report_name!)).toBeInTheDocument();

        act(() => { jest.advanceTimersByTime(POLLING_INTERVAL); });
        expect(mockGetReportTaskStatus).toHaveBeenCalledTimes(3);
    });
});
```

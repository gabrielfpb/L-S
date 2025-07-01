import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterMoment } from '@mui/x-date-pickers/AdapterMoment';
import '@testing-library/jest-dom';

import DashboardPage from './DashboardPage';
import * as cointegrationService from '../services/cointegrationService';
import { AuthContext, User } from '../contexts/AuthContext';

// Mock Plotly component
jest.mock('react-plotly.js', () => ({
    __esModule: true,
    default: jest.fn(() => <div data-testid="plotly-chart-mock"></div>),
}));

const theme = createTheme();
const mockUser: User = {id:1, username:'test', email:'test@test.com', is_active:true, is_superuser: false};
const mockAuthContextValue = {
    isAuthenticated: true, user: mockUser,
    token: 'fake-token', login: jest.fn(), logout: jest.fn(), isLoading: false, error: null
};

// Helper to wrap component in necessary providers
const renderDashboardPage = () => {
    return render(
        <AuthContext.Provider value={mockAuthContextValue}>
            <ThemeProvider theme={theme}>
                <LocalizationProvider dateAdapter={AdapterMoment}>
                    <BrowserRouter><DashboardPage /></BrowserRouter>
                </LocalizationProvider>
            </ThemeProvider>
        </AuthContext.Provider>
    );
};

describe('DashboardPage - Advanced Charts and Interactions', () => {
    beforeEach(() => {
        jest.clearAllMocks(); // Reset mocks before each test
    });

    test('renders chart parameter controls (DatePicker, TextField for window)', () => {
        renderDashboardPage();
        expect(screen.getByLabelText(/Start Date/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/End Date/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Z-Score Window/i)).toBeInTheDocument();
    });

    test('calls getHistoricalPairData and renders chart on "Chart Details" button click', async () => {
        const mockPairData: cointegrationService.IdentifiedPairData = {
            pair_yx: ["YLD.SA", "XFIX.SA"], adf_statistic: -3.8, p_value: 0.02,
            hedge_ratio_beta_x: 0.5, current_zscore_of_spread: -2.2, n_observations_in_test: 200
        };
        const mockHistoricalApiResponse: cointegrationService.HistoricalPairDataResponseFE = {
            ticker_y: "YLD.SA", ticker_x: "XFIX.SA", timestamps: [new Date().toISOString()],
            prices_y: [110], prices_x: [55], spread: [1.5], spread_mean: [0.8],
            spread_std_dev_upper_1: [1.2], spread_std_dev_lower_1: [0.4],
            spread_std_dev_upper_2: [1.6], spread_std_dev_lower_2: [0.0],
            z_score: [-2.1], calculated_hedge_ratio_beta_x: 0.52
        };

        const mockIdentify = jest.spyOn(cointegrationService, 'identifyCointegratedPairs')
                                 .mockResolvedValueOnce({ pairs: [mockPairData], summary_message: "1 pair found", } as any);
        const mockFetchHistorical = jest.spyOn(cointegrationService, 'getHistoricalPairData')
                                      .mockResolvedValue(mockHistoricalApiResponse);

        renderDashboardPage();

        fireEvent.change(screen.getByLabelText(/Tickers \(comma-separated\)/i), { target: { value: 'YLD.SA,XFIX.SA' } });
        fireEvent.click(screen.getByRole('button', { name: /Identify \/ Re-Identify Pairs/i }));

        await waitFor(() => expect(mockIdentify).toHaveBeenCalled());

        const viewDetailsButton = await screen.findByRole('button', { name: /Chart Details/i });
        fireEvent.click(viewDetailsButton);

        await waitFor(() => expect(mockFetchHistorical).toHaveBeenCalledTimes(1));
        expect(mockFetchHistorical).toHaveBeenCalledWith(expect.objectContaining({
            ticker_y: "YLD.SA", ticker_x: "XFIX.SA"
        }));

        expect(screen.getByTestId('plotly-chart-mock')).toBeInTheDocument();
    });

    test('refresh button for Z-Scores calls handleIdentifyPairs with isRefresh=true', async () => {
        const mockPairData: cointegrationService.IdentifiedPairData = {
            pair_yx: ["REFRESH.SA", "ME.SA"], adf_statistic: -3.8, p_value: 0.02,
            hedge_ratio_beta_x: 0.5, current_zscore_of_spread: -2.2, n_observations_in_test: 200
        };
        const mockIdentify = jest.spyOn(cointegrationService, 'identifyCointegratedPairs')
                                 .mockResolvedValue({ pairs: [mockPairData], summary_message: "1 pair found", } as any);

        renderDashboardPage();

        fireEvent.change(screen.getByLabelText(/Tickers \(comma-separated\)/i), { target: { value: 'REFRESH.SA,ME.SA' } });
        fireEvent.click(screen.getByRole('button', { name: /Identify \/ Re-Identify Pairs/i }));
        await waitFor(() => expect(mockIdentify).toHaveBeenCalledTimes(1));

        const refreshButton = await screen.findByRole('button', { name: /Refresh List & Z-Scores/i});
        fireEvent.click(refreshButton);

        await waitFor(() => expect(mockIdentify).toHaveBeenCalledTimes(2));
        expect(screen.getByText(/Last updated:/i)).toBeInTheDocument();
    });

});
```

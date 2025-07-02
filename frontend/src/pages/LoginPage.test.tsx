import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import '@testing-library/jest-dom';

import LoginPage from './LoginPage';
import * as authService from '../services/authService'; // To mock loginUser
import { AuthContext, User } from '../contexts/AuthContext'; // To provide mock AuthContext
import { NotificationContext } from '../contexts/NotificationContext'; // To provide mock NotificationContext

const theme = createTheme();
const mockUser: User = { id: 1, username: 'testuser', email: 'test@example.com', is_active: true, is_superuser: false };
const mockAuthContextValue = {
    isAuthenticated: false, // Initially not authenticated for login page
    user: null,
    token: null,
    login: jest.fn(), // Mock the login function from AuthContext
    logout: jest.fn(),
    isLoading: false,
    error: null,
};

// Helper to wrap component in necessary providers
const renderLoginPage = (mockShowNotificationFunc: jest.Mock) => {
    // Allow passing a specific mock for showNotification per test scenario if needed
    return render(
        <AuthContext.Provider value={mockAuthContextValue}>
            <NotificationContext.Provider value={{ showNotification: mockShowNotificationFunc }}>
                <ThemeProvider theme={theme}>
                    <BrowserRouter><LoginPage /></BrowserRouter>
                </ThemeProvider>
            </NotificationContext.Provider>
        </AuthContext.Provider>
    );
};

describe('LoginPage - Notifications', () => {
    let mockLoginUser: jest.SpyInstance;
    const mockShowNotification = jest.fn();

    beforeEach(() => {
        jest.clearAllMocks();
        mockLoginUser = jest.spyOn(authService, 'loginUser'); // Spy on loginUser from authService
    });

    test('calls showNotification on successful login', async () => {
        mockLoginUser.mockResolvedValue({ token: 'fake-token', user: mockUser });

        renderLoginPage(mockShowNotification);

        fireEvent.change(screen.getByLabelText(/Username/i), { target: { value: 'testuser' } });
        fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: 'password' } });
        fireEvent.click(screen.getByRole('button', { name: /Sign In/i }));

        await waitFor(() => {
            expect(mockAuthContextValue.login).toHaveBeenCalledWith('fake-token', mockUser); // Check AuthContext login
            expect(mockShowNotification).toHaveBeenCalledWith('Login successful!', 'success');
        });
    });

    test('calls showNotification on login failure', async () => {
        const errorMessage = 'Invalid credentials';
        mockLoginUser.mockRejectedValue(new Error(errorMessage));

        renderLoginPage(mockShowNotification);

        fireEvent.change(screen.getByLabelText(/Username/i), { target: { value: 'testuser' } });
        fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: 'password' } });
        fireEvent.click(screen.getByRole('button', { name: /Sign In/i }));

        await waitFor(() => {
            expect(mockShowNotification).toHaveBeenCalledWith(errorMessage, 'error');
            // Also check that local error alert on the form might be shown
            expect(screen.getByText(errorMessage)).toBeInTheDocument();
        });
    });
});
```

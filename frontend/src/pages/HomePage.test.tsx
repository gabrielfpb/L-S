import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom'; // For components using RouterLink
import HomePage from './HomePage'; // Adjust path as needed
import { ThemeProvider, createTheme } from '@mui/material/styles';
import '@testing-library/jest-dom'; // For .toBeInTheDocument()

// Mock useAuth if HomePage or its children use it (not strictly needed for current HomePage)
// jest.mock('../contexts/AuthContext', () => ({
//   useAuth: () => ({
//     isAuthenticated: false, // or true, depending on test case
//     user: null,
//     // ... other mocked auth context values
//   }),
// }));

const theme = createTheme(); // Use a default theme for rendering MUI components

describe('HomePage', () => {
    test('renders welcome message and key buttons', () => {
        render(
            <ThemeProvider theme={theme}>
                <BrowserRouter>
                    <HomePage />
                </BrowserRouter>
            </ThemeProvider>
        );

        // Check for welcome message
        expect(screen.getByText(/Welcome to Long & Short Quant/i)).toBeInTheDocument();

        // Check for key buttons/links
        expect(screen.getByRole('button', { name: /Go to Dashboard/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Login/i })).toBeInTheDocument();
    });

    test('dashboard button links to /dashboard', () => {
        render(
            <ThemeProvider theme={theme}>
                <BrowserRouter>
                    <HomePage />
                </BrowserRouter>
            </ThemeProvider>
        );
        const dashboardButton = screen.getByRole('button', { name: /Go to Dashboard/i });
        // For RouterLink, check the href attribute of the underlying <a> tag
        expect(dashboardButton.closest('a')).toHaveAttribute('href', '/dashboard');
    });

    test('login button links to /login', () => {
        render(
            <ThemeProvider theme={theme}>
                <BrowserRouter>
                    <HomePage />
                </BrowserRouter>
            </ThemeProvider>
        );
        const loginButton = screen.getByRole('button', { name: /Login/i });
        expect(loginButton.closest('a')).toHaveAttribute('href', '/login');
    });
});

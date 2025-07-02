// frontend/src/contexts/NotificationContext.tsx
/**
 * @module NotificationContext
 * Provides a global notification system using Material-UI Snackbar and Alert components.
 *
 * Usage:
 * 1. Wrap your application (or a relevant part) with `<NotificationProvider>`.
 * 2. In any child component, use the `useNotifier()` hook to get the `showNotification` function.
 * 3. Call `showNotification('Your message', 'success' | 'error' | 'info' | 'warning')` to display a notification.
 */
import React, { createContext, useState, useContext, ReactNode, useCallback } from 'react';
import { Snackbar, Alert, AlertColor } from '@mui/material';

/**
 * @interface NotificationContextType
 * Defines the shape of the notification context, primarily the `showNotification` function.
 */
interface NotificationContextType {
    showNotification: (message: string, severity?: AlertColor) => void;
}

/**
 * @interface NotificationState
 * Internal state for the NotificationProvider.
 * @property {boolean} open - Controls Snackbar visibility.
 * @property {string} message - The message to display.
 * @property {AlertColor} severity - The severity of the alert (e.g., 'success', 'error').
 * @property {number} key - A unique key to force Snackbar re-render for consecutive identical messages.
 */
interface NotificationState {
    open: boolean;
    message: string;
    severity: AlertColor;
    key: number;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

/**
 * @component NotificationProvider
 * Manages the state for the global Snackbar notification and provides the
 * `showNotification` function to its children via context.
 * Renders the MUI Snackbar and Alert components.
 * @param {object} props - Component props.
 * @param {ReactNode} props.children - Child components to be wrapped by the provider.
 */
export const NotificationProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [notification, setNotification] = useState<NotificationState>({
        open: false,
        message: '',
        severity: 'info', // Default severity
        key: new Date().getTime(),
    });

    /**
     * Displays a notification message.
     * @param {string} message - The message content.
     * @param {AlertColor} [severity='info'] - The severity of the notification ('success', 'error', 'info', 'warning').
     */
    const showNotification = useCallback((message: string, severity: AlertColor = 'info') => {
        setNotification({
            open: true,
            message,
            severity,
            key: new Date().getTime(), // New key forces Snackbar to re-render if message is same
        });
    }, []);

    const handleClose = (event?: React.SyntheticEvent | Event, reason?: string) => {
        if (reason === 'clickaway') {
            return;
        }
        setNotification((prev) => ({ ...prev, open: false }));
    };

    return (
        <NotificationContext.Provider value={{ showNotification }}>
            {children}
            <Snackbar
                key={notification.key}
                open={notification.open}
                autoHideDuration={6000} // Hide after 6 seconds
                onClose={handleClose}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
            >
                <Alert onClose={handleClose} severity={notification.severity} sx={{ width: '100%' }} variant="filled">
                    {notification.message}
                </Alert>
            </Snackbar>
        </NotificationContext.Provider>
    );
};

/**
 * @function useNotifier
 * Custom hook to easily access the `showNotification` function from the NotificationContext.
 * Must be used within a component wrapped by `<NotificationProvider>`.
 * @throws {Error} If used outside of a NotificationProvider.
 * @returns {NotificationContextType} The notification context value containing `showNotification`.
 */
export const useNotifier = (): NotificationContextType => {
    const context = useContext(NotificationContext);
    if (context === undefined) {
        throw new Error('useNotifier must be used within a NotificationProvider');
    }
    return context;
};
```

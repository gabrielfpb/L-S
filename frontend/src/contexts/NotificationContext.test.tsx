import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { NotificationProvider, useNotifier } from './NotificationContext';
import { Button } from '@mui/material'; // To trigger notification

jest.useFakeTimers(); // For autoHideDuration

const TestComponent: React.FC<{ msg?: string, severity?: any }> = ({ msg = "Test Message", severity = "success" }) => {
    const notifier = useNotifier();
    return (
        <Button onClick={() => notifier.showNotification(msg, severity)}>
            Show Notification
        </Button>
    );
};

describe('NotificationContext', () => {
    test('NotificationProvider provides showNotification function', () => {
        let notifier: any;
        const ConsumerComponent = () => {
            notifier = useNotifier();
            return null;
        };
        render(
            <NotificationProvider>
                <ConsumerComponent />
            </NotificationProvider>
        );
        expect(notifier.showNotification).toBeDefined();
        expect(typeof notifier.showNotification).toBe('function');
    });

    test('Snackbar appears with correct message and severity when showNotification is called', () => {
        render(
            <NotificationProvider>
                <TestComponent msg="Success!" severity="success" />
            </NotificationProvider>
        );

        // Snackbar is not visible initially
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();

        // Click button to show notification
        fireEvent.click(screen.getByText('Show Notification'));

        // Snackbar should appear with Alert role
        const alert = screen.getByRole('alert');
        expect(alert).toBeInTheDocument();
        expect(alert).toHaveTextContent('Success!');
        // Check severity (MUI Alert adds class like .MuiAlert-filledSuccess)
        expect(alert).toHaveClass('MuiAlert-filledSuccess');
    });

    test('Snackbar auto-hides after autoHideDuration', () => {
        render(
            <NotificationProvider>
                <TestComponent />
            </NotificationProvider>
        );

        fireEvent.click(screen.getByText('Show Notification'));
        expect(screen.getByRole('alert')).toBeInTheDocument(); // Visible

        // Fast-forward timers by autoHideDuration (default 6000ms)
        act(() => {
            jest.advanceTimersByTime(6000);
        });

        // Snackbar should be hidden
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    test('Snackbar can show consecutive messages even if identical by using key', () => {
         render(
            <NotificationProvider>
                <TestComponent msg="Same Message" severity="info" />
            </NotificationProvider>
        );

        // First notification
        fireEvent.click(screen.getByText('Show Notification'));
        const alert1 = screen.getByRole('alert');
        expect(alert1).toBeInTheDocument();
        expect(alert1).toHaveTextContent('Same Message');

        // Close it by advancing timer
        act(() => { jest.advanceTimersByTime(6000); });
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();

        // Second notification with the same message
        fireEvent.click(screen.getByText('Show Notification'));
        const alert2 = screen.getByRole('alert');
        expect(alert2).toBeInTheDocument();
        expect(alert2).toHaveTextContent('Same Message');
    });
});
```

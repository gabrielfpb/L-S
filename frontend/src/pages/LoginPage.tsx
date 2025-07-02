import React, { useState } from 'react';
import { Typography, Container, Paper, TextField, Button, Box, Alert } from '@mui/material';
import { useNavigate, Link as RouterLink, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import * as authService from '../services/authService';
import { useNotifier } from '../contexts/NotificationContext'; // Corrected import

const LoginPage: React.FC = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState<string | null>(null); // Local form error
    const [isLoading, setIsLoading] = useState(false);
    const auth = useAuth();
    const navigate = useNavigate();
    const location = useLocation(); // To get 'from' state for redirect after login
    const notifier = useNotifier(); // Get showNotification

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault();
        setError(null); // Clear local error
        setIsLoading(true);
        try {
            const { token, user } = await authService.loginUser({ username, password });
            auth.login(token, user);
            notifier.showNotification('Login successful!', 'success');
            // Redirect to the page user was trying to access, or dashboard
            const from = location.state?.from?.pathname || '/dashboard';
            navigate(from, { replace: true });
        } catch (err: any) {
            const errorMsg = err.message || 'Failed to login. Please check your credentials.';
            setError(errorMsg); // Set local error for the form alert
            notifier.showNotification(errorMsg, 'error'); // Show global snackbar notification
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Container component="main" maxWidth="xs" sx={{ mt: 8 }}>
            <Paper elevation={3} sx={{ padding: 4, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography component="h1" variant="h5">
                    Sign In
                </Typography>
                {error && <Alert severity="error" sx={{ width: '100%', mt: 2 }}>{error}</Alert>}
                <Box component="form" onSubmit={handleSubmit} noValidate sx={{ mt: 1 }}>
                    <TextField
                        margin="normal" required fullWidth id="username" label="Username" name="username"
                        autoComplete="username" autoFocus value={username} onChange={(e) => setUsername(e.target.value)}
                    />
                    <TextField
                        margin="normal" required fullWidth name="password" label="Password" type="password"
                        id="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)}
                    />
                    <Button type="submit" fullWidth variant="contained" sx={{ mt: 3, mb: 2 }} disabled={isLoading}>
                        {isLoading ? 'Signing In...' : 'Sign In'}
                    </Button>
                    <Box textAlign="center">
                         <RouterLink to="/register"> {/* Add link to registration page */}
                            {"Don't have an account? Sign Up"}
                        </RouterLink>
                    </Box>
                </Box>
            </Paper>
        </Container>
    );
};
export default LoginPage;

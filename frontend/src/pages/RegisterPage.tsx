import React, { useState } from 'react';
import { Typography, Container, Paper, TextField, Button, Box, Alert } from '@mui/material';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import * as authService from '../services/authService';
import { useNotifier } from '../contexts/NotificationContext'; // Import useNotifier

const RegisterPage: React.FC = () => {
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [fullName, setFullName] = useState('');
    const [error, setError] = useState<string | null>(null); // Local form error
    const [success, setSuccess] = useState<string | null>(null); // Local form success message
    const [isLoading, setIsLoading] = useState(false);
    const navigate = useNavigate();
    const notifier = useNotifier(); // Get showNotification

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault();
        setError(null); // Clear local messages
        setSuccess(null);
        setIsLoading(true);
        try {
            await authService.registerUser({ username, email, password, full_name: fullName });
            const successMsg = 'Registration successful! You can now log in.';
            setSuccess(successMsg); // Show local success message on form
            notifier.showNotification(successMsg, 'success'); // Show global snackbar
            // Optionally redirect after a delay or provide a button to go to login
            // For now, user sees success message and can click the link below.
            // setTimeout(() => navigate('/login'), 3000);
        } catch (err: any) {
            const errorMsg = err.message || 'Failed to register. Please try again.';
            setError(errorMsg); // Show local error on form
            notifier.showNotification(errorMsg, 'error'); // Show global snackbar
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Container component="main" maxWidth="xs" sx={{ mt: 8 }}>
            <Paper elevation={3} sx={{ padding: 4, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography component="h1" variant="h5">
                    Sign Up
                </Typography>
                {error && <Alert severity="error" sx={{ width: '100%', mt: 2 }}>{error}</Alert>}
                {success && <Alert severity="success" sx={{ width: '100%', mt: 2 }}>{success}</Alert>}
                <Box component="form" onSubmit={handleSubmit} noValidate sx={{ mt: 1 }}>
                    <TextField margin="normal" required fullWidth label="Username" value={username} onChange={(e) => setUsername(e.target.value)} />
                    <TextField margin="normal" required fullWidth label="Email Address" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
                    <TextField margin="normal" required fullWidth label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
                    <TextField margin="normal" fullWidth label="Full Name (Optional)" value={fullName} onChange={(e) => setFullName(e.target.value)} />
                    <Button type="submit" fullWidth variant="contained" sx={{ mt: 3, mb: 2 }} disabled={isLoading}>
                        {isLoading ? 'Signing Up...' : 'Sign Up'}
                    </Button>
                    <Box textAlign="center">
                        <RouterLink to="/login">
                            {"Already have an account? Sign In"}
                        </RouterLink>
                    </Box>
                </Box>
            </Paper>
        </Container>
    );
};
export default RegisterPage;

import React, { useState } from 'react';
import { Typography, Container, Paper, TextField, Button, Box, Alert } from '@mui/material';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import * as authService from '../services/authService'; // Import your auth service

const LoginPage: React.FC = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const auth = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault();
        setError(null);
        setIsLoading(true);
        try {
            const { token, user } = await authService.loginUser({ username, password });
            auth.login(token, user); // Update auth context
            navigate('/dashboard'); // Redirect to dashboard or intended page
        } catch (err: any) {
            setError(err.message || 'Failed to login. Please check your credentials.');
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

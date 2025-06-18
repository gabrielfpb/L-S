import React, { useState } from 'react';
import { Typography, Container, Paper, TextField, Button, Box, Alert } from '@mui/material';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import * as authService from '../services/authService'; // Import your auth service

const RegisterPage: React.FC = () => {
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [fullName, setFullName] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault();
        setError(null);
        setSuccess(null);
        setIsLoading(true);
        try {
            await authService.registerUser({ username, email, password, full_name: fullName });
            setSuccess('Registration successful! Please login.');
            // setTimeout(() => navigate('/login'), 2000); // Optional redirect after delay
        } catch (err: any) {
            setError(err.message || 'Failed to register. Please try again.');
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

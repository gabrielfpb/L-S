import React from 'react';
import { Typography, Container, Button } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';

const HomePage: React.FC = () => {
    return (
        <Container>
            <Typography variant="h3" component="h1" gutterBottom sx={{mt: 4}}>
                Welcome to Long & Short Quant
            </Typography>
            <Typography variant="h6" paragraph>
                Your modern and responsive application for financial analysis and trading.
            </Typography>
            <Button variant="contained" color="primary" component={RouterLink} to="/dashboard" sx={{mr: 2}}>
                Go to Dashboard
            </Button>
            <Button variant="outlined" component={RouterLink} to="/login">
                Login
            </Button>
        </Container>
    );
};
export default HomePage;

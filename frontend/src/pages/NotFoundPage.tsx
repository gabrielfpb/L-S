import React from 'react'; import { Typography, Container, Button } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
const NotFoundPage: React.FC = () => (
    <Container sx={{textAlign: 'center', mt: 8}}>
        <Typography variant="h3" gutterBottom>404 - Page Not Found</Typography>
        <Typography variant="body1">The page you are looking for does not exist.</Typography>
        <Button variant="contained" component={RouterLink} to="/" sx={{mt:3}}>Go Home</Button>
    </Container>
);
export default NotFoundPage;

import React from 'react';
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Container, Button } from '@mui/material';

function HomePage() {
  return (
    <Container>
      <Typography variant="h4" component="h1" gutterBottom>
        Welcome to Long & Short Quant
      </Typography>
      <Typography>
        This is the placeholder homepage.
      </Typography>
    </Container>
  );
}

function App() {
  return (
    <Router>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Long & Short Quant
          </Typography>
          <Button color="inherit" component={Link} to="/">Home</Button>
          {/* Add other navigation links here */}
        </Toolbar>
      </AppBar>
      <Container sx={{ marginTop: '2rem' }}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          {/* Define other routes here */}
        </Routes>
      </Container>
    </Router>
  );
}

export default App;

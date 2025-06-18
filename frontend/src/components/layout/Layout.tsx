import React, { useState } from 'react';
import { Box, Toolbar, CssBaseline } from '@mui/material';
import Navbar from './Navbar';
import Sidebar from './Sidebar'; // Assuming you have a Sidebar component

interface LayoutProps {
    children: React.ReactNode;
}

const drawerWidth = 240; // Define your drawer width

const Layout: React.FC<LayoutProps> = ({ children }) => {
    const [isSidebarOpen, setSidebarOpen] = useState(false);

    const handleSidebarToggle = () => {
        setSidebarOpen(!isSidebarOpen);
    };

    const handleSidebarClose = () => {
        setSidebarOpen(false);
    };

    return (
        <Box sx={{ display: 'flex' }}>
            <CssBaseline /> {/* Handles baseline styling like background color */}
            <Navbar onToggleSidebar={handleSidebarToggle} isSidebarOpen={isSidebarOpen} />
            <Sidebar
                isOpen={isSidebarOpen}
                onClose={handleSidebarClose}
                drawerWidth={drawerWidth}
            />
            <Box
                component="main"
                sx={{
                    flexGrow: 1,
                    p: 3, // padding
                    width: { sm: `calc(100% - ${drawerWidth}px)` }, // Adjust width if sidebar is persistent/permanent
                    // marginLeft: { sm: `${isSidebarOpen ? drawerWidth : 0}px` }, // Example if sidebar pushes content
                    transition: (theme) => theme.transitions.create(['margin', 'width'], {
                        easing: theme.transitions.easing.sharp,
                        duration: theme.transitions.duration.leavingScreen,
                    }),
                }}
            >
                <Toolbar /> {/* This is crucial to ensure content is below the AppBar */}
                {children}
            </Box>
        </Box>
    );
};

export default Layout;

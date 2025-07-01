import React from 'react';
import { Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText, Toolbar, Box } from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import ShowChartIcon from '@mui/icons-material/ShowChart'; // For Trades/Positions
import AssessmentIcon from '@mui/icons-material/Assessment';
import SettingsIcon from '@mui/icons-material/Settings';
import { Link as RouterLink, useLocation } from 'react-router-dom'; // Import useLocation

interface SidebarProps {
    isOpen: boolean;
    onClose: () => void;
    drawerWidth?: number;
}

const defaultDrawerWidth = 240;

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose, drawerWidth = defaultDrawerWidth }) => {
    const menuItems = [
        { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
        { text: 'Trade Management', icon: <ShowChartIcon />, path: '/trades' },
        { text: 'Reports', icon: <AssessmentIcon />, path: '/reports' },
        { text: 'Settings', icon: <SettingsIcon />, path: '/settings' },
    ];

    const location = useLocation(); // Get current location

    return (
        <Drawer
            variant="temporary"
            open={isOpen}
            onClose={onClose}
            sx={{
                width: drawerWidth,
                flexShrink: 0,
                [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box' },
            }}
        >
            <Toolbar /> {/* Necessary to offset content below AppBar */}
            <Box sx={{ overflow: 'auto' }}>
                <List>
                    {menuItems.map((item) => (
                        <ListItem key={item.text} disablePadding component={RouterLink} to={item.path} sx={{ color: 'text.primary', textDecoration: 'none'}}>
                            <ListItemButton
                                onClick={onClose}
                                selected={location.pathname === item.path || (item.path !== "/" && location.pathname.startsWith(item.path))}
                            >
                                <ListItemIcon sx={{color: location.pathname.startsWith(item.path) ? 'primary.main' : 'inherit'}}>
                                    {item.icon}
                                </ListItemIcon>
                                <ListItemText primary={item.text} />
                            </ListItemButton>
                        </ListItem>
                    ))}
                </List>
            </Box>
        </Drawer>
    );
};

export default Sidebar;

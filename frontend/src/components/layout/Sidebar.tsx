import React from 'react';
import { Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText, Toolbar, Box } from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import ShowChartIcon from '@mui/icons-material/ShowChart'; // For Trades/Positions
import AssessmentIcon from '@mui/icons-material/Assessment'; // For Reports
import SettingsIcon from '@mui/icons-material/Settings'; // Example
import { Link as RouterLink } from 'react-router-dom';

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
        { text: 'Settings', icon: <SettingsIcon />, path: '/settings' }, // Example
    ];

    return (
        <Drawer
            variant="temporary" // Or "permanent" or "persistent" based on design
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
                        <ListItem key={item.text} disablePadding component={RouterLink} to={item.path} sx={{ color: 'inherit', textDecoration: 'none'}}>
                            <ListItemButton onClick={onClose}> {/* Close sidebar on item click */}
                                <ListItemIcon>
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

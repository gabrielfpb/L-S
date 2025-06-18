import React from 'react';
import { AppBar, Toolbar, Typography, Button, IconButton, Box, Avatar, Menu, MenuItem, Tooltip } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext'; // Import useAuth

interface NavbarProps {
    onToggleSidebar?: () => void;
    isSidebarOpen?: boolean;
}

const Navbar: React.FC<NavbarProps> = ({ onToggleSidebar, isSidebarOpen }) => {
    const { isAuthenticated, user, logout } = useAuth(); // Use auth context
    const navigate = useNavigate();
    const [anchorElUser, setAnchorElUser] = React.useState<null | HTMLElement>(null);

    const handleLogout = () => {
        logout();
        navigate('/login'); // Redirect to login after logout
        handleCloseUserMenu();
    };

    const handleOpenUserMenu = (event: React.MouseEvent<HTMLElement>) => {
        setAnchorElUser(event.currentTarget);
    };

    const handleCloseUserMenu = () => {
        setAnchorElUser(null);
    };

    const userSettings = [ // Menu items for logged-in user
        // { label: 'Profile', action: () => { navigate('/profile'); handleCloseUserMenu(); } }, // TODO: Create /profile page
        { label: 'Settings', action: () => { navigate('/settings'); handleCloseUserMenu(); } },
        { label: 'Logout', action: handleLogout },
    ];

    return (
        <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
            <Toolbar>
                {isAuthenticated && onToggleSidebar && ( // Show sidebar toggle only if authenticated and sidebar exists
                     <IconButton color="inherit" aria-label="toggle drawer" edge="start" onClick={onToggleSidebar} sx={{ mr: 2 }}>
                        <MenuIcon />
                    </IconButton>
                )}
                <Typography variant="h6" noWrap component={RouterLink} to="/" sx={{ flexGrow: 1, color: 'inherit', textDecoration: 'none' }}>
                    Long & Short Quant
                </Typography>

                {isAuthenticated && user ? (
                    <Box sx={{ flexGrow: 0 }}>
                        <Tooltip title="Open settings">
                            <IconButton onClick={handleOpenUserMenu} sx={{ p: 0 }}>
                                <Avatar alt={user.username.toUpperCase()} src="/static/images/avatar/2.jpg" />
                                {/* Replace src with actual user avatar if available */}
                            </IconButton>
                        </Tooltip>
                        <Menu
                            sx={{ mt: '45px' }}
                            id="menu-appbar"
                            anchorEl={anchorElUser}
                            anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
                            keepMounted
                            transformOrigin={{ vertical: 'top', horizontal: 'right' }}
                            open={Boolean(anchorElUser)}
                            onClose={handleCloseUserMenu}
                        >
                            <MenuItem disabled>
                                <Typography textAlign="center" variant="subtitle2" sx={{ fontWeight: 'bold' }}>{user.username}</Typography>
                            </MenuItem>
                            {userSettings.map((setting) => (
                                <MenuItem key={setting.label} onClick={setting.action}>
                                    <Typography textAlign="center">{setting.label}</Typography>
                                </MenuItem>
                            ))}
                        </Menu>
                    </Box>
                ) : (
                    <>
                        <Button color="inherit" component={RouterLink} to="/login">Login</Button>
                        <Button color="inherit" component={RouterLink} to="/register">Sign Up</Button>
                    </>
                )}
            </Toolbar>
        </AppBar>
    );
};
export default Navbar;

import React, { createContext, useState, useContext, useEffect, ReactNode } from 'react';
// Assume an authService will be created for API calls
// For now, we can mock the login/logout logic or prepare for it.
import * as authService from '../services/authService'; // Placeholder, will create next

interface AuthContextType {
    isAuthenticated: boolean;
    user: User | null; // Define a User type based on your backend UserResponse
    token: string | null;
    login: (token: string, userData: User) => void; // Simplified: in real app, login calls API
    logout: () => void;
    isLoading: boolean; // To handle loading state during auth operations
    error: string | null; // To display auth errors
    // register: (userData: RegisterData) => Promise<void>; // Example for registration
}

// Define a simple User type, align with backend's UserResponse
export interface User { // Exporting User type for use in other files like authService
    id: number;
    username: string;
    email: string;
    full_name?: string | null;
    is_active: boolean;
    is_superuser?: boolean; // Optional based on your needs
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(localStorage.getItem('authToken'));
    const [isLoading, setIsLoading] = useState<boolean>(true); // Start true to check initial auth
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const attemptAutoLogin = async () => {
            const currentToken = localStorage.getItem('authToken'); // Use fresh token from storage
            if (currentToken) {
                setIsLoading(true);
                try {
                    // Fetch current user data using the token
                    const userData = await authService.fetchCurrentUser(currentToken);
                    setUser(userData);
                    setToken(currentToken); // Ensure token state is also updated
                    localStorage.setItem('authUser', JSON.stringify(userData)); // Refresh stored user
                } catch (err) {
                    console.error("Auto login failed", err);
                    localStorage.removeItem('authToken');
                    localStorage.removeItem('authUser');
                    setToken(null);
                    setUser(null);
                    // setError("Session expired. Please login again."); // Optional: set error for UI
                } finally {
                    setIsLoading(false);
                }
            } else {
                setIsLoading(false); // No token, not loading
            }
        };
        attemptAutoLogin();
    }, []); // Run only on mount

    const login = (newToken: string, userData: User) => {
        localStorage.setItem('authToken', newToken);
        localStorage.setItem('authUser', JSON.stringify(userData));
        setToken(newToken);
        setUser(userData);
        setError(null); // Clear previous errors
    };

    const logout = () => {
        localStorage.removeItem('authToken');
        localStorage.removeItem('authUser');
        setToken(null);
        setUser(null);
        // Optionally redirect to login page via useNavigate() hook in the component calling logout
    };

    return (
        <AuthContext.Provider value={{ isAuthenticated: !!token && !!user, user, token, login, logout, isLoading, error }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = (): AuthContextType => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

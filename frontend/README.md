# Frontend - Long & Short Quant

This directory contains the React (with TypeScript and Material-UI) frontend application.

## Overview
The frontend provides the user interface for interacting with the Long & Short Quant application, including:
*   User Authentication (Login, Registration pages)
*   Protected Routes for authenticated sections
*   Cointegration Dashboard (Pair identification, Z-Score viewing, basic charts)
*   Trade Management (Listing, Creating, Closing trades)
*   Reporting (Requesting summary/backtest reports, Listing generated reports with download links)
*   A responsive layout with Navbar and Sidebar for navigation.

## Local Development (Without Docker)

1.  **Prerequisites**:
    *   Node.js (version 16.x or 18.x recommended)
    *   npm or yarn

2.  **Install Dependencies**:
    Navigate to the `frontend/` directory:
    ```bash
    npm install
    # OR, if you prefer yarn:
    # yarn install
    ```

3.  **Configure Environment Variables**:
    *   Create a `.env` file in this `frontend/` directory (you can copy `.env.example` if one is provided, or create it manually).
    *   The primary environment variable used for connecting to the backend API is:
        *   `REACT_APP_API_BASE_URL`: The base URL for the backend API.
            *   When running the frontend locally and the backend is also running locally (e.g., on port 8000 via `uvicorn` or Docker exposing the port), set this to:
                ```env
                REACT_APP_API_BASE_URL=http://localhost:8000/api/v1
                ```
            *   If this variable is not set, `src/services/api.ts` defaults to `/api/v1`. This default is suitable when the frontend is served by Nginx (like in the Docker setup) which proxies requests from `/api/v1` (on the same host as frontend) to the backend service.

4.  **Run Development Server**:
    ```bash
    npm start
    # OR
    # yarn start
    ```
    This will typically open the application in your browser at `http://localhost:3000`. The development server provides hot reloading.

## Build for Production
To create an optimized static build of the application:
```bash
npm run build
# OR
# yarn build
```
This command bundles the app into static files in the `build/` directory. The `Dockerfile` for the frontend uses this command to prepare assets for Nginx.

## Folder Structure (`src/`)
*   `App.tsx`: Main application component, sets up ThemeProvider, Router, AuthProvider, and Layout. Defines global routes.
*   `index.tsx`: Root React file, renders `App` into the DOM.
*   `components/`: Contains reusable UI components.
    *   `layout/`: Components for the main application layout (Navbar, Sidebar, Layout).
    *   `auth/`: Components related to authentication (e.g., `ProtectedRoute`).
*   `contexts/`: React Context API providers, currently `AuthContext.tsx` for managing authentication state globally.
*   `pages/`: Top-level components representing different pages/views of the application (e.g., `DashboardPage.tsx`, `LoginPage.tsx`).
*   `services/`: Modules for making API calls to the backend.
    *   `api.ts`: Configures the main Axios instance (`apiClient`), including base URL and interceptors (e.g., for attaching auth tokens).
    *   Other files like `authService.ts`, `cointegrationService.ts`, `tradeService.ts`, `reportService.ts` define specific API interaction functions.
*   `assets/`: (Currently empty) For static assets like images, custom fonts, etc.
*   `store/`: (Currently a placeholder) Intended for more complex state management (e.g., Redux Toolkit) if the application's state needs grow beyond what Context API comfortably handles.

## Key Libraries & Features
*   **React Router (`react-router-dom`)**: For declarative client-side routing and navigation.
*   **Material-UI (MUI)**: Comprehensive UI component library for layout, inputs, tables, dialogs, etc., enabling a consistent and professional look and feel.
*   **Axios**: Promise-based HTTP client for making requests to the backend API.
*   **Plotly.js & `react-plotly.js`**: Used for rendering interactive charts (currently a basic Z-score chart on the Dashboard).
*   **React Context API (`AuthContext`)**: Manages global authentication state (user, token, loading status) and provides login/logout functions throughout the app.
*   **TypeScript**: For static typing, improving code quality and maintainability.

## Testing
(Placeholder - Instructions for running frontend tests, e.g., with Jest and React Testing Library)
Example:
```bash
# npm test
# OR
# yarn test
```

This README provides essential information for setting up and running the frontend application in a local development environment. For deployment, refer to the root `README.md` and `Dockerfile` for building a production-ready container.
```

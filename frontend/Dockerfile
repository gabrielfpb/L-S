# frontend/Dockerfile

# Stage 1: Build the React app
FROM node:18-alpine AS build

WORKDIR /app

COPY package.json ./
COPY package-lock.json ./
# If using yarn:
# COPY yarn.lock ./
# RUN yarn install --frozen-lockfile

RUN npm install

COPY . .

# Set the API URL for the build (can be overridden at runtime by Nginx if needed, or fixed here)
# If REACT_APP_API_BASE_URL is used by api.ts, it should be set here or in .env for build stage.
# For Docker Compose, Nginx will proxy, so frontend can call /api/v1 directly.
# Ensure your api.ts in frontend/src/services/api.ts uses a relative path like '/api/v1'
# or an environment variable that can be configured.
# If REACT_APP_API_BASE_URL is used, it should be set in the .env file copied, or here:
# ENV REACT_APP_API_BASE_URL=/api/v1
# If your api.ts is already configured to use a relative path like /api/v1 (ideal for this setup),
# no specific ENV is needed here for REACT_APP_API_BASE_URL.
RUN npm run build

# Stage 2: Serve the app using Nginx
FROM nginx:stable-alpine

# Copy built static files from the build stage
COPY --from=build /app/build /usr/share/nginx/html

# Copy Nginx configuration
# This nginx.conf should be configured to serve the React app and proxy API requests
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

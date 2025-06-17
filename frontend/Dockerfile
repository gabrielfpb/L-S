# Stage 1: Build the React app
FROM node:18 AS build

WORKDIR /app

COPY package.json ./
COPY package-lock.json ./
# yarn install --frozen-lockfile
RUN npm install

COPY . .

RUN npm run build

# Stage 2: Serve the app using Nginx
FROM nginx:stable-alpine

COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

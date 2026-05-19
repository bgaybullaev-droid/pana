# Stage 1: Build
FROM node:20-alpine AS build

WORKDIR /app

# Build args for Vite env variables
ARG VITE_API_URL
ARG VITE_IMAGE_BASE_URL
ARG VITE_ALLOW_DESKTOP
ARG VITE_APP_NAME
ARG VITE_ENV
ARG VITE_SELLER_BOT_USERNAME
ARG VITE_BUYER_BOT_USERNAME
ARG VITE_MINI_APP_SHORT_NAME

# Set env variables for build
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_IMAGE_BASE_URL=$VITE_IMAGE_BASE_URL
ENV VITE_ALLOW_DESKTOP=$VITE_ALLOW_DESKTOP
ENV VITE_APP_NAME=$VITE_APP_NAME
ENV VITE_ENV=$VITE_ENV
ENV VITE_SELLER_BOT_USERNAME=$VITE_SELLER_BOT_USERNAME
ENV VITE_BUYER_BOT_USERNAME=$VITE_BUYER_BOT_USERNAME
ENV VITE_MINI_APP_SHORT_NAME=$VITE_MINI_APP_SHORT_NAME

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built files from build stage
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]

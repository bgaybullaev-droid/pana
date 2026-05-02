# Stage 1: build the Vite app
FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_API_URL
ARG VITE_IMAGE_BASE_URL
ARG VITE_ALLOW_DESKTOP
ARG VITE_APP_NAME
ARG VITE_ENV
ARG VITE_SELLER_BOT_USERNAME
ARG VITE_BUYER_BOT_USERNAME
ARG VITE_MINI_APP_SHORT_NAME

ENV VITE_API_URL=$VITE_API_URL \
    VITE_IMAGE_BASE_URL=$VITE_IMAGE_BASE_URL \
    VITE_ALLOW_DESKTOP=$VITE_ALLOW_DESKTOP \
    VITE_APP_NAME=$VITE_APP_NAME \
    VITE_ENV=$VITE_ENV \
    VITE_SELLER_BOT_USERNAME=$VITE_SELLER_BOT_USERNAME \
    VITE_BUYER_BOT_USERNAME=$VITE_BUYER_BOT_USERNAME \
    VITE_MINI_APP_SHORT_NAME=$VITE_MINI_APP_SHORT_NAME

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: serve with nginx
FROM nginx:mainline-alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80 443
CMD ["nginx", "-g", "daemon off;"]

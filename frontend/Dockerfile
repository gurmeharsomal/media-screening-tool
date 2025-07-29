# MIT License
# Copyright (c) 2024 Media Screening Tool

# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy all frontend files
COPY . .

# Install dependencies
RUN npm ci

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built application
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"] 
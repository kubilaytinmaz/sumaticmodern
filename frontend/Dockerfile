# =============================================================================
# Sumatic Modern IoT - Frontend Dockerfile
# Simplified single-stage build for Coolify compatibility
# =============================================================================

FROM node:20-alpine

# Install libc6-compat for Alpine compatibility
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install all dependencies
RUN npm install

# Copy source code
COPY . .

# Set environment variables for build
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_WS_URL=ws://localhost:8000

ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL} \
    NODE_ENV=production

# Show environment info for debugging
RUN echo "=== BUILD INFO ===" && \
    echo "Node version: $(node --version)" && \
    echo "NPM version: $(npm --version)" && \
    echo "NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL}" && \
    echo "NEXT_PUBLIC_WS_URL: ${NEXT_PUBLIC_WS_URL}" && \
    echo "NODE_ENV: ${NODE_ENV}" && \
    echo "=================="

# Type check first to show TypeScript errors clearly
RUN echo "=== TYPE CHECK ===" && \
    npx tsc --noEmit 2>&1 || echo "TypeScript check warnings (non-fatal)"

# Build the application with verbose output
RUN echo "=== STARTING NPM BUILD ===" && \
    npm run build 2>&1 && \
    echo "=== BUILD SUCCESS ==="

# Expose port
EXPOSE 3000

# Set port and hostname
ENV PORT=3000 \
    HOSTNAME="0.0.0.0"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

# Start the application
CMD ["npm", "start"]

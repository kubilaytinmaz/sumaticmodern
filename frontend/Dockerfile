# =============================================================================
# Sumatic Modern IoT - Frontend Dockerfile
# Simplified single-stage build for Coolify compatibility
# =============================================================================

FROM node:20-alpine

# Install libc6-compat for Alpine compatibility
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Set NODE_ENV to development for dependency installation
ENV NODE_ENV=development \
    NEXT_TELEMETRY_DISABLED=1

# Copy package files
COPY package.json package-lock.json* ./

# Install all dependencies (including devDependencies)
# Force NODE_ENV=development to ensure devDependencies are installed
RUN NODE_ENV=development npm install

# Copy source code
COPY . .

# Build arguments for environment variables
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL
ARG NODE_ENV=development

# Set environment variables from build args
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-http://localhost:8000} \
    NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL:-ws://localhost:8000} \
    NODE_ENV=${NODE_ENV:-development}

# Build the application
# Force NODE_ENV=development to ensure build works correctly
RUN NODE_ENV=development npm run build

# Set environment to production for runtime
ENV NODE_ENV=production

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

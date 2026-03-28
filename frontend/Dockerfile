# =============================================================================
# Sumatic Modern IoT - Frontend Dockerfile
# Multi-stage build for optimized production image
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Dependencies
# -----------------------------------------------------------------------------
FROM node:20-alpine AS deps

# Install libc6-compat for Alpine compatibility
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Set NODE_ENV to development for dependency installation
ENV NODE_ENV=development

# Copy package files
COPY package.json package-lock.json* yarn.lock* ./

# Debug: Show package files
RUN echo "=== DEPS STAGE DEBUG ===" && \
    echo "NODE_ENV: $NODE_ENV" && \
    echo "Package files:" && \
    ls -la && \
    echo "========================"

# Install dependencies (including devDependencies regardless of NODE_ENV)
RUN npm install

# -----------------------------------------------------------------------------
# Stage 2: Builder
# -----------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Set environment variables for build
ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=development

# Build arguments for environment variables
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL
ARG NODE_ENV=development

# Set environment variables from build args
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-http://localhost:8000} \
    NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL:-ws://localhost:8000} \
    NODE_ENV=${NODE_ENV:-development}

# Debug: Show environment and node version before build
RUN echo "=== BUILD DEBUG INFO ===" && \
    echo "NODE_ENV: $NODE_ENV" && \
    echo "Node version: $(node --version)" && \
    echo "NPM version: $(npm --version)" && \
    echo "Working directory: $(pwd)" && \
    echo "Files in directory:" && \
    ls -la && \
    echo "========================"

# Debug: Check if node_modules are present
RUN echo "=== NODE_MODULES CHECK ===" && \
    ls -la node_modules | head -20 && \
    echo "============================"

# Build the application with verbose output
RUN NODE_ENV=development npm run build --verbose

# -----------------------------------------------------------------------------
# Stage 3: Production Runner
# -----------------------------------------------------------------------------
FROM node:20-alpine AS runner

# Labels
LABEL maintainer="Sumatic Team" \
      app.name="sumatic-frontend" \
      app.version="1.0.0"

WORKDIR /app

# Set environment to production
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy necessary files from builder
COPY --from=builder /app/public ./public

# Set up standalone output directory
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Switch to non-root user
USER nextjs

# Expose port
EXPOSE 3000

# Set port and hostname
ENV PORT=3000 \
    HOSTNAME="0.0.0.0"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

# Start the application
CMD ["node", "server.js"]

# -----------------------------------------------------------------------------
# Stage 4: Development (optional)
# -----------------------------------------------------------------------------
FROM node:20-alpine AS development

WORKDIR /app

# Install dependencies
RUN apk add --no-cache libc6-compat

# Copy package files
COPY package.json package-lock.json* yarn.lock* ./

# Install all dependencies (including devDependencies)
RUN \
  if [ -f yarn.lock ]; then yarn; \
  elif [ -f package-lock.json ]; then npm install; \
  else npm install; \
  fi

# Copy source code
COPY . .

# Set environment variables
ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=development

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

# Start development server
CMD ["npm", "run", "dev"]

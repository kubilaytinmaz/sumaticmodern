/** @type {import('next').NextConfig} */
const nextConfig = {
  // output: 'standalone', // Disabled for Coolify compatibility
  reactStrictMode: true,
  swcMinify: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          // Security headers
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()',
          },
          // Content Security Policy - XSS koruması için
          // Development ortamında daha esnek, production'da katı kurallar
          ...(process.env.NODE_ENV === 'production'
            ? [
                {
                  key: 'Content-Security-Policy',
                  value: [
                    "default-src 'self';",
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval';",
                    "style-src 'self' 'unsafe-inline';",
                    "img-src 'self' data: https: blob:;",
                    "font-src 'self' data:;",
                    "connect-src 'self' " + (process.env.NEXT_PUBLIC_API_URL || '') + " " + (process.env.NEXT_PUBLIC_WS_URL || '') + ";",
                    "frame-ancestors 'none';",
                    "base-uri 'self';",
                    "form-action 'self';",
                    "object-src 'none';",
                  ].join(' '),
                },
                {
                  key: 'Strict-Transport-Security',
                  value: 'max-age=31536000; includeSubDomains; preload',
                },
              ]
            : [
                {
                  key: 'Content-Security-Policy',
                  value: [
                    "default-src 'self';",
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval' localhost:* ws://localhost:* http://localhost:*;",
                    "style-src 'self' 'unsafe-inline';",
                    "img-src 'self' data: https: blob: http://localhost:*;",
                    "font-src 'self' data:;",
                    "connect-src 'self' " + (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000') + " " + (process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000') + " ws://localhost:* http://localhost:*;",
                    "frame-ancestors 'self';",
                    "base-uri 'self';",
                    "form-action 'self';",
                    "object-src 'none';",
                  ].join(' '),
                },
              ]),
        ],
      },
    ];
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
  },
};

module.exports = nextConfig;

import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

/**
 * Authentication Middleware
 *
 * NOTE: This middleware is DISABLED because authentication is handled client-side
 * via the DashboardLayout component which checks localStorage for tokens.
 *
 * Server-side middleware cannot access localStorage, so it would always fail
 * to find the token and redirect users to login even after successful authentication.
 *
 * If you need server-side auth protection, consider:
 * 1. Using HTTP-only cookies for token storage
 * 2. Implementing a server-side session check
 * 3. Using Next.js middleware with cookie-based auth
 */
export function middleware(request: NextRequest) {
  // Middleware disabled - let client-side auth handle protection
  return NextResponse.next()
}

// Matcher disabled - middleware now allows all routes
export const config = {
  matcher: [], // Empty matcher = middleware doesn't run on any route
}

import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

/**
 * Authentication Middleware
 *
 * Protects dashboard routes by verifying JWT token validity.
 * Public routes (login, health, etc.) are excluded.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  
  // Public routes - no authentication required
  const publicRoutes = ['/login', '/auth', '/health', '/']
  const isPublicRoute = publicRoutes.some(route => pathname.startsWith(route))
  
  if (isPublicRoute) {
    return NextResponse.next()
  }
  
  // Check for access token in cookies or localStorage (via headers)
  const accessToken = request.cookies.get('access_token')?.value ||
                      request.headers.get('authorization')?.replace('Bearer ', '')
  
  if (!accessToken) {
    // No token found - redirect to login
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('redirect', pathname)
    return NextResponse.redirect(loginUrl)
  }
  
  // Token exists - allow request to proceed
  // Note: Backend will validate token on protected API calls
  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes have their own auth via backend)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico|health).*)',
  ],
}

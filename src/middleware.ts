import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(req: NextRequest) {
  // Exemplo de verificação simples via cookie do Supabase Auth
  // Se você tem rotas específicas a proteger, inclua na lógica.
  const authCookie = req.cookies.get('sb-access-token') || req.cookies.get('supabase-auth-token')
  
  // Rotas que queremos proteger (exemplo: dashboard, settings)
  const protectedRoutes = ['/dashboard', '/settings', '/alerts']
  const isProtectedRoute = protectedRoutes.some(route => req.nextUrl.pathname.startsWith(route))

  if (isProtectedRoute && !authCookie) {
    // Redireciona para login se não estiver logado
    const loginUrl = new URL('/login', req.url)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
}

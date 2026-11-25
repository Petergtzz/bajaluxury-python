import { type NextRequest, NextResponse } from 'next/server'

import { createClient } from '@/lib/api/client'
import { encodeUser, getAPIURL, SESSION_COOKIE, USER_HEADER } from '@/lib/api/session'
import type { User } from '@/lib/api/types'

const PUBLIC_ROUTES = [/^\/login(\/.*)?$/]

const getUser = async (request: NextRequest): Promise<User | null> => {
  if (!request.cookies.has(SESSION_COOKIE)) return null
  const api = createClient(getAPIURL(), { Cookie: request.headers.get('cookie') ?? '' })
  const { data, response } = await api.GET('/v1/users/me', { cache: 'no-store' })
  if (response.status === 401) return null
  if (!data) {
    throw new Error(`Unexpected ${response.status} from /v1/users/me`)
  }
  return data
}

/**
 * Resolves who is visiting once per page: strangers go to the login page,
 * and the page gets the user in a header instead of asking the API again.
 */
export async function proxy(request: NextRequest) {
  const headers = new Headers(request.headers)
  headers.delete(USER_HEADER)
  const user = await getUser(request)
  const { pathname, search } = request.nextUrl
  const open = PUBLIC_ROUTES.some((route) => route.test(pathname))
  if (!user && !open) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    url.search = ''
    if (pathname !== '/') url.searchParams.set('return_to', `${pathname}${search}`)
    return NextResponse.redirect(url)
  }
  if (user) headers.set(USER_HEADER, encodeUser(user))
  return NextResponse.next({ request: { headers } })
}

export const config = {
  // Everything but the API (passed on to the server) and Next's own files.
  matcher: [
    '/((?!v1/|_next/static|_next/image|favicon.ico|icon.png|logo.png|logo-mark.png).*)',
  ],
}

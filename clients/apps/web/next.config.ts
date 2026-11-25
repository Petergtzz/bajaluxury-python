import type { NextConfig } from 'next'

const apiUrl = process.env.BAJA_API_URL ?? 'http://127.0.0.1:8100'

/** Nothing frames the dashboard or redirects where its forms post. */
const securityHeaders = [
  {
    key: 'Content-Security-Policy',
    value:
      "frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'",
  },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
]

const nextConfig: NextConfig = {
  output: 'standalone',
  poweredByHeader: false,
  // Dev is opened at 127.0.0.1, where the API sets its cookie; Next would
  // treat it as another origin than localhost and refuse it the hot reload.
  allowedDevOrigins: ['127.0.0.1'],
  // The API's collection routes end in "/"; Next would redirect them away.
  skipTrailingSlashRedirect: true,
  async headers() {
    return [{ source: '/:path*', headers: securityHeaders }]
  },
  // The browser only ever calls its own origin: no CORS, no tokens in it.
  async rewrites() {
    return [
      // `:path*` never captures a trailing slash, so collections get their own.
      { source: '/v1/:path*/', destination: `${apiUrl}/v1/:path*/` },
      { source: '/v1/:path*', destination: `${apiUrl}/v1/:path*` },
    ]
  },
}

export default nextConfig

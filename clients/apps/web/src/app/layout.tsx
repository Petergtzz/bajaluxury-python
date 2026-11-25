import type { Metadata } from 'next'
import { Manrope } from 'next/font/google'
import type { ReactNode } from 'react'

import { Providers } from './providers'
import './globals.css'

const manrope = Manrope({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-manrope',
})

export const metadata: Metadata = {
  title: { default: 'Baja Luxury', template: '%s - Baja Luxury' },
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={manrope.variable} suppressHydrationWarning>
      <body className="font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}

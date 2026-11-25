'use client'

import { QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from 'next-themes'
import type { ReactNode } from 'react'

import { Toaster } from '@/components/ui/sonner'
import { getQueryClient } from '@/lib/query'

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={getQueryClient()}>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
        {children}
        <Toaster />
      </ThemeProvider>
    </QueryClientProvider>
  )
}

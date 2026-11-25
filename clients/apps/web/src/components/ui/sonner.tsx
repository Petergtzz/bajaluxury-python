'use client'

import { useTheme } from 'next-themes'
import { Toaster as Sonner } from 'sonner'

export function Toaster() {
  const { resolvedTheme } = useTheme()
  return (
    <Sonner
      theme={resolvedTheme === 'dark' ? 'dark' : 'light'}
      position="bottom-center"
      toastOptions={{ classNames: { toast: 'rounded-2xl! font-sans!' } }}
    />
  )
}

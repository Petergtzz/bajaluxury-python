'use client'

import type { ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

/**
 * What a dialog can do besides saving - Archive, Delete, Remove, Turn off - as
 * text buttons under the full-width primary one. They are quieter than it on
 * purpose, and each that can't be undone asks first.
 */
export function DialogActions({ children }: { children: ReactNode }) {
  return <div className="-mt-2 grid gap-1">{children}</div>
}

export function TextAction({
  children,
  onClick,
  destructive,
  disabled,
}: {
  children: ReactNode
  onClick: () => void
  /** Red, for what removes something. */
  destructive?: boolean
  disabled?: boolean
}) {
  return (
    <Button
      type="button"
      variant="ghost"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        'h-11 w-full rounded-full text-[15px] font-medium',
        destructive &&
          'text-destructive-foreground hover:bg-destructive/10 hover:text-destructive-foreground dark:hover:bg-destructive/20',
      )}
    >
      {children}
    </Button>
  )
}

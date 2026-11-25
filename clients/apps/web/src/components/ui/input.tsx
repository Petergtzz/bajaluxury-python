import type { ComponentProps } from 'react'

import { cn } from '@/lib/utils'

export function Input({ className, ...props }: ComponentProps<'input'>) {
  return (
    <input
      className={cn(
        'flex h-11 w-full min-w-0 rounded-xl border border-input bg-transparent px-4 text-[15px] outline-none transition-[color,box-shadow] placeholder:text-muted-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:opacity-50 aria-invalid:border-destructive',
        className,
      )}
      {...props}
    />
  )
}

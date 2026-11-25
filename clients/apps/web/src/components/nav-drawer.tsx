'use client'

import * as DialogPrimitive from '@radix-ui/react-dialog'
import type { ReactNode } from 'react'

/** The sidebar slid in over the page, below a laptop's width. */
export function NavDrawer({
  open,
  onOpenChange,
  children,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  children: ReactNode
}) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/30 data-[state=open]:animate-in data-[state=open]:fade-in-0 lg:hidden" />
        <DialogPrimitive.Content className="fixed inset-y-0 left-0 z-50 w-[min(19rem,85vw)] overflow-y-auto bg-background shadow-xl outline-none data-[state=open]:animate-in data-[state=open]:slide-in-from-left lg:hidden">
          <DialogPrimitive.Title className="sr-only">Navigation</DialogPrimitive.Title>
          {children}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}

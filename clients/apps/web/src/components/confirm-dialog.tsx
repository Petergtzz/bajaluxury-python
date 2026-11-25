'use client'

import type { ReactNode } from 'react'

import { InputError } from '@/components/input-error'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Spinner } from '@/components/ui/spinner'

/** "Are you sure" for something that can't be undone, in the delete dialog's style. */
export function ConfirmDialog({
  title,
  children,
  action,
  open,
  onOpenChange,
  onConfirm,
  pending,
  error,
}: {
  title: string
  children: ReactNode
  /** The button's words, like "Delete category". */
  action: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
  pending: boolean
  error?: string
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader className="text-left">
          {/* leading-4 matches the close button's 16px box, so the title and
              the X sit on the same line. */}
          <DialogTitle className="text-base leading-4 font-medium">{title}</DialogTitle>
        </DialogHeader>

        <div className="text-sm text-muted-foreground">{children}</div>
        <InputError message={error} />

        <Button
          type="button"
          variant="destructive"
          disabled={pending}
          onClick={onConfirm}
          className="h-12 w-full rounded-full text-base font-semibold"
        >
          {pending && <Spinner className="size-5" />}
          {action}
        </Button>
      </DialogContent>
    </Dialog>
  )
}

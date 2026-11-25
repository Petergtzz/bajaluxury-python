'use client'

import type { FormEvent, ReactNode } from 'react'

import { DialogActions } from '@/components/dialog-actions'
import { InputError } from '@/components/input-error'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Spinner } from '@/components/ui/spinner'
import { cn } from '@/lib/utils'

/**
 * A dialog that asks for something and saves it.
 *
 * Every one of them was the same eighteen lines - the width, the title's size,
 * the grid the fields sit in, a centred error under them and a full-width pill
 * that spins while it saves - around fields that are all that actually differ.
 * They share those lines here, so the next one cannot drift from the rest.
 *
 * What a dialog does on its way in or out of the page belongs to the dialog:
 * pass `contentProps` for the odd one that has to keep focus off a field.
 */
export function FormDialog({
  title,
  open,
  onOpenChange,
  onSubmit,
  submitLabel,
  pending,
  disabled,
  error,
  destructive,
  className,
  contentProps,
  actions,
  children,
}: {
  title: ReactNode
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: () => void
  /** What the button says, which is what pressing it does. */
  submitLabel: ReactNode
  /** Spins the button and holds it, while the save is in the air. */
  pending?: boolean
  /** Holds the button for a reason of the form's own, like an empty field. */
  disabled?: boolean
  error?: string
  /** Colours the button red, for what cannot be undone by pressing it again. */
  destructive?: boolean
  /** Extra classes for the panel, for a dialog that has to scroll. */
  className?: string
  contentProps?: React.ComponentProps<typeof DialogContent>
  /** What else it can do, as `TextAction`s under the button: Archive, Delete. */
  actions?: ReactNode
  children: ReactNode
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={cn('sm:max-w-md', className)} {...contentProps}>
        <DialogHeader className="text-left">
          <DialogTitle className="text-base leading-4 font-medium">{title}</DialogTitle>
        </DialogHeader>

        <form
          className="grid gap-4"
          noValidate
          onSubmit={(event: FormEvent) => {
            event.preventDefault()
            onSubmit()
          }}
        >
          {children}

          <InputError message={error} className="text-center" />

          <Button
            type="submit"
            variant={destructive ? 'destructive' : 'default'}
            disabled={pending || disabled}
            className="h-12 w-full rounded-full text-base font-semibold"
          >
            {pending && <Spinner className="size-5" />}
            {submitLabel}
          </Button>
          {actions && <DialogActions>{actions}</DialogActions>}
        </form>
      </DialogContent>
    </Dialog>
  )
}

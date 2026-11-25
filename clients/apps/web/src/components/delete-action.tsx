'use client'

import { useState } from 'react'

import { Button } from '@/components/ui/button'

/**
 * A dialog's quiet way to delete what it shows: a red text button that asks
 * once more before anything happens.
 */
export function DeleteAction({
  label,
  busy,
  onDelete,
}: {
  label: string
  busy: boolean
  onDelete: () => void
}) {
  const [confirming, setConfirming] = useState(false)
  const red = 'font-semibold text-destructive'
  return confirming ? (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-muted-foreground">Delete it for good?</span>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className={red}
        onClick={onDelete}
        disabled={busy}
      >
        Delete
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => setConfirming(false)}
      >
        Keep
      </Button>
    </div>
  ) : (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      className={red}
      onClick={() => setConfirming(true)}
    >
      {label}
    </Button>
  )
}

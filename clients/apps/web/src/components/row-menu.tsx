'use client'

import { MoreHorizontal } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

export type RowMenuItem = {
  label: string
  onSelect: () => void
  destructive?: boolean
}

/**
 * The "…" at the end of a row that opens nothing, with what can be done to it.
 * A row that opens a dialog has a chevron instead, and its actions live in the
 * dialog.
 */
export function RowMenu({
  label,
  items,
}: {
  /** Names the row for screen readers, like "More for Colinas 21". */
  label: string
  items: RowMenuItem[]
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="size-9 shrink-0 rounded-lg"
          aria-label={label}
        >
          <MoreHorizontal className="size-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        {items.map((item) => (
          <DropdownMenuItem
            key={item.label}
            variant={item.destructive ? 'destructive' : 'default'}
            onSelect={item.onSelect}
          >
            {item.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

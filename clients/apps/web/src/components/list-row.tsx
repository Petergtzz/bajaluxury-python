'use client'

import { ChevronRight } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

/**
 * A row in any list: a round mark, a name with a quiet line under it, and
 * something at the end. A row that opens something is wholly its button and
 * ends in a chevron; one that opens nothing ends in what it shows.
 */
export function ListRow({
  mark,
  title,
  meta,
  trailing,
  label,
  onSelect,
}: {
  mark: ReactNode
  title: ReactNode
  meta?: ReactNode
  trailing?: ReactNode
  /** What a screen reader hears for the row's button. */
  label?: string
  onSelect?: () => void
}) {
  const content = (
    <>
      {mark}
      <span className="min-w-0 flex-1">
        <span className="block truncate text-base font-semibold text-neutral-900 dark:text-neutral-100">
          {title}
        </span>
        {meta && (
          <span className="mt-0.5 flex min-w-0 items-center gap-1.5 text-sm text-muted-foreground">
            {meta}
          </span>
        )}
      </span>
      {trailing}
    </>
  )
  return (
    // Hovered, the row lifts onto a soft card reaching just past its content.
    <li
      className={cn(
        '-mx-2 rounded-xl px-2 transition-colors duration-150 sm:-mx-4 sm:px-4',
        onSelect &&
          'hover:bg-neutral-100 has-[:focus-visible]:bg-neutral-100 has-[:focus-visible]:ring-[3px] has-[:focus-visible]:ring-ring/50 dark:hover:bg-neutral-800/70 dark:has-[:focus-visible]:bg-neutral-800/70',
      )}
    >
      {onSelect ? (
        <button type="button" onClick={onSelect} aria-label={label} className={ROW}>
          {content}
          <ChevronRight
            className="-mr-1 size-5 shrink-0 text-muted-foreground"
            aria-hidden
          />
        </button>
      ) : (
        <div className={ROW}>{content}</div>
      )}
    </li>
  )
}

const ROW = 'flex w-full min-w-0 items-center gap-4 py-3.5 text-left outline-none'

/** The round mark at the start of a row. */
export function RowMark({
  className,
  children,
}: {
  className?: string
  children: ReactNode
}) {
  return (
    <span
      className={cn(
        'flex size-11 shrink-0 items-center justify-center rounded-full bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300',
        className,
      )}
    >
      {children}
    </span>
  )
}

/** What the rows under it are: a day, "5 properties". */
export function ListHeading({ children }: { children: ReactNode }) {
  return (
    <h2 className="border-b border-border pb-3 text-sm text-muted-foreground">
      {children}
    </h2>
  )
}

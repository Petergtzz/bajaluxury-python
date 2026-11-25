'use client'

import { cn } from '@/lib/utils'

/** The few views a page offers, as pills, with a count inside its own. */
export function TabPills<T extends string>({
  label,
  tabs,
  current,
  onSelect,
  labels,
  counts,
}: {
  label: string
  tabs: readonly T[]
  current: T
  onSelect: (tab: T) => void
  labels: Record<T, string>
  counts?: Partial<Record<T, number | undefined>>
}) {
  return (
    <div role="tablist" aria-label={label} className="flex flex-wrap gap-2">
      {tabs.map((tab) => {
        const selected = tab === current
        const count = counts?.[tab]
        return (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={selected}
            onClick={() => onSelect(tab)}
            className={cn(
              'flex h-11 items-center gap-2 rounded-full px-5 text-[15px] font-semibold transition-colors',
              selected
                ? 'bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900'
                : 'bg-neutral-100 text-neutral-900 hover:bg-neutral-200/70 dark:bg-neutral-800/70 dark:text-neutral-100 dark:hover:bg-neutral-800',
            )}
          >
            {labels[tab]}
            {count ? (
              <span
                className={cn(
                  'inline-flex h-6 min-w-6 items-center justify-center rounded-full px-1.5 text-xs tabular-nums',
                  selected
                    ? 'bg-white/20 text-white dark:bg-neutral-900/15 dark:text-neutral-900'
                    : 'bg-neutral-200/80 dark:bg-neutral-700',
                )}
              >
                {count}
              </span>
            ) : null}
          </button>
        )
      })}
    </div>
  )
}

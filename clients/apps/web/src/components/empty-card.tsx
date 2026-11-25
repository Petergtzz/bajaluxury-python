import type { ReactNode } from 'react'

/** A list with nothing in it, said on a card so the page doesn't look broken. */
export function EmptyCard({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-3xl bg-neutral-50 px-6 py-16 text-center dark:bg-neutral-800/50">
      <p className="text-base font-semibold text-neutral-900 dark:text-neutral-100">
        {title}
      </p>
      {children && <p className="text-sm text-muted-foreground">{children}</p>}
    </div>
  )
}

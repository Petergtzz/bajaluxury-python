import type { ReactNode } from 'react'

import { TriangleAlert } from 'lucide-react'

/**
 * The one place on a page where something raises its voice.
 *
 * Rows stay quiet and uniform, so a row that needed attention would be lost
 * among them; this says it once, above them all. An <output> announces itself
 * to a screen reader without shouting.
 */
export function WarningNotice({ children }: { children: ReactNode }) {
  return (
    <output className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-2xl bg-amber-50 px-5 py-4 text-[15px] text-amber-900 dark:bg-amber-500/10 dark:text-amber-200">
      <TriangleAlert className="size-[18px] shrink-0" aria-hidden />
      <span>{children}</span>
    </output>
  )
}

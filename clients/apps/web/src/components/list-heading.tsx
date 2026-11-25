import type { ReactNode } from 'react'

/**
 * What the rows under it are: a day in the ledger, "5 properties", "Members".
 *
 * A quiet line with a rule under it, so a list can be broken into parts without
 * boxes or headers that weigh more than the rows they introduce.
 */
export function ListHeading({ children }: { children: ReactNode }) {
  return (
    <h2 className="border-b border-border pb-3 text-sm text-muted-foreground">
      {children}
    </h2>
  )
}

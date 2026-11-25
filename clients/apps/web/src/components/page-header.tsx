import type { ComponentProps, ReactNode } from 'react'

import { Button } from '@/components/ui/button'

/**
 * A page's one action that makes or sends something. A round icon on a
 * phone, where the title's line is short; a labelled pill from `sm` up.
 */
export function PageAction({
  label,
  icon,
  ...props
}: { label: string; icon: ReactNode } & Omit<ComponentProps<typeof Button>, 'children'>) {
  return (
    <Button
      className="size-11 gap-2 rounded-full p-0 text-[15px] font-semibold has-[>svg]:px-0 sm:h-11 sm:w-auto sm:px-5 sm:has-[>svg]:px-5 [&>svg]:size-5 sm:[&>svg]:size-4"
      {...props}
    >
      {icon}
      <span className="sr-only sm:not-sr-only">{label}</span>
    </Button>
  )
}

/**
 * The top of a page: its name, what it is for, and its action. Nothing sits
 * above it, so the title is large and carries the page.
 */
export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string
  description?: ReactNode
  actions?: ReactNode
}) {
  return (
    // The action stays on the title's line, a phone's too; what the page is
    // for goes under both.
    <header>
      <div className="flex min-h-11 items-start justify-between gap-x-6 gap-y-4">
        <h1 className="min-w-0 text-3xl font-bold tracking-tight text-neutral-900 sm:text-[34px] dark:text-neutral-100">
          {title}
        </h1>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
      {description && (
        <p className="mt-2 text-[15px] text-muted-foreground">{description}</p>
      )}
    </header>
  )
}

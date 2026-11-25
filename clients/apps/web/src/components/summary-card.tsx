import type { ReactNode } from 'react'

const LABEL = 'text-sm text-muted-foreground'

export type Figure = { label: string; value: ReactNode | undefined }

/**
 * The figures over a list, on a grey card: one large, the question the page
 * is opened to answer, and the few that make it up beneath it. A figure still
 * loading is a grey bar of its size, so nothing jumps when it arrives.
 */
export function SummaryCard({
  label,
  headline,
  figures,
}: {
  label: string
  headline: ReactNode | undefined
  figures: Figure[]
}) {
  return (
    <section
      aria-label="Summary"
      className="rounded-3xl bg-neutral-50 px-6 py-7 sm:px-9 sm:py-8 dark:bg-neutral-800/50"
    >
      <div className={`mb-1.5 ${LABEL}`}>{label}</div>
      <div className="flex flex-col gap-6">
        <p className="min-w-0 text-[32px] font-bold tracking-tight whitespace-nowrap text-neutral-900 tabular-nums sm:text-5xl dark:text-neutral-100">
          {headline ?? (
            <span className="inline-block h-10 w-56 animate-pulse rounded-md bg-muted align-middle sm:h-12" />
          )}
        </p>
        <dl className="flex flex-wrap gap-x-10 gap-y-4 sm:flex-nowrap [&>div+div]:sm:border-l [&>div+div]:sm:pl-10">
          {figures.map((figure) => (
            <div key={figure.label}>
              <dt className={LABEL}>{figure.label}</dt>
              <dd className="mt-1.5 text-lg font-semibold tracking-tight whitespace-nowrap text-neutral-900 tabular-nums sm:text-2xl dark:text-neutral-100">
                {figure.value ?? (
                  <span className="inline-block h-6 w-28 animate-pulse rounded-md bg-muted" />
                )}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  )
}

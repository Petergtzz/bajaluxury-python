import type { TransactionSummary } from '@/lib/api/types'
import { formatMoney } from '@/lib/format'

const LABEL = 'text-sm text-muted-foreground'

/**
 * The figures over the list: what is left for the period, then what made it.
 * Money in is green with its sign, money out plain: spending is a house's
 * normal business, not an alarm.
 */
export function LedgerSummary({
  summary,
  period,
  currency,
}: {
  summary: TransactionSummary | undefined
  period: string
  currency: string
}) {
  const net = summary ? summary.income_total - summary.expense_total : undefined
  return (
    <section
      aria-label="Summary"
      className="rounded-3xl bg-neutral-50 px-6 py-7 sm:px-9 sm:py-8 dark:bg-neutral-800/50"
    >
      <div className={`mb-1.5 ${LABEL}`}>Net · {period}</div>
      <div className="flex flex-col gap-6">
        <p className="min-w-0 text-[32px] font-bold tracking-tight whitespace-nowrap text-neutral-900 tabular-nums sm:text-5xl dark:text-neutral-100">
          {net !== undefined ? (
            formatMoney(net, currency)
          ) : (
            <span className="inline-block h-10 w-56 animate-pulse rounded-md bg-muted align-middle sm:h-12" />
          )}
        </p>
        <dl className="flex flex-wrap gap-x-10 gap-y-4 sm:flex-nowrap [&>div+div]:sm:border-l [&>div+div]:sm:pl-10">
          <Figure label="Money in">
            {summary && (
              <span className="text-emerald-700 dark:text-emerald-500">
                +{formatMoney(summary.income_total, currency)}
              </span>
            )}
          </Figure>
          <Figure label="Money out">
            {summary && formatMoney(summary.expense_total, currency)}
          </Figure>
          <Figure label="Entries">{summary?.count.toLocaleString('en-US')}</Figure>
        </dl>
      </div>
    </section>
  )
}

function Figure({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className={LABEL}>{label}</dt>
      <dd className="mt-1.5 text-lg font-semibold tracking-tight whitespace-nowrap text-neutral-900 tabular-nums sm:text-2xl dark:text-neutral-100">
        {children ?? (
          <span className="inline-block h-6 w-28 animate-pulse rounded-md bg-muted" />
        )}
      </dd>
    </div>
  )
}

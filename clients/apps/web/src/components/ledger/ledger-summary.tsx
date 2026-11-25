import { SummaryCard } from '@/components/summary-card'
import type { TransactionSummary } from '@/lib/api/types'
import { useMoney } from '@/components/session-context'

/**
 * What is left for the period, then what made it. Money in is green with its
 * sign, money out plain: spending is a house's normal business, not an alarm.
 */
export function LedgerSummary({
  summary,
  period,
}: {
  summary: TransactionSummary | undefined
  period: string
}) {
  const money = useMoney()
  return (
    <SummaryCard
      label={`Net · ${period}`}
      headline={summary && money(summary.income_total - summary.expense_total)}
      figures={[
        {
          label: 'Money in',
          value: summary && (
            <span className="text-emerald-700 dark:text-emerald-500">
              +{money(summary.income_total)}
            </span>
          ),
        },
        {
          label: 'Money out',
          value: summary && money(summary.expense_total),
        },
        { label: 'Entries', value: summary?.count.toLocaleString('en-US') },
      ]}
    />
  )
}

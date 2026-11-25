import { SummaryCard } from '@/components/summary-card'
import type { TransactionSummary } from '@/lib/api/types'
import { formatMoney } from '@/lib/format'

/**
 * What is left for the period, then what made it. Money in is green with its
 * sign, money out plain: spending is a house's normal business, not an alarm.
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
  return (
    <SummaryCard
      label={`Net · ${period}`}
      headline={
        summary && formatMoney(summary.income_total - summary.expense_total, currency)
      }
      figures={[
        {
          label: 'Money in',
          value: summary && (
            <span className="text-emerald-700 dark:text-emerald-500">
              +{formatMoney(summary.income_total, currency)}
            </span>
          ),
        },
        {
          label: 'Money out',
          value: summary && formatMoney(summary.expense_total, currency),
        },
        { label: 'Entries', value: summary?.count.toLocaleString('en-US') },
      ]}
    />
  )
}

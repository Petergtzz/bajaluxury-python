import type { ReactNode } from 'react'

import { ListRow } from '@/components/list-row'
import type { Property, Transaction } from '@/lib/api/types'
import { useMoney } from '@/components/session-context'
import { formatDayHeading, groupConsecutive, sentence } from '@/lib/format'
import { cn } from '@/lib/utils'

import { MethodMark } from './method-icon'

/**
 * The ledger as days, each heading its transactions. A row carries what a
 * glance needs: what it was, for which property, how it was paid, how much.
 */
export function TransactionsList({
  transactions,
  properties,
  today,
  empty,
  onSelect,
}: {
  transactions: Transaction[]
  properties: Map<string, Property>
  today: string
  empty: ReactNode
  onSelect: (transaction: Transaction) => void
}) {
  const money = useMoney()
  if (transactions.length === 0) {
    return <div className="p-6 text-center text-sm text-muted-foreground">{empty}</div>
  }
  return (
    <div className="flex flex-col gap-9">
      {groupConsecutive(transactions, (one) => one.date).map((day) => (
        <section key={day.key} aria-label={formatDayHeading(day.key, today)}>
          <h2 className="border-b border-border pb-3 text-sm text-muted-foreground">
            {formatDayHeading(day.key, today)}
          </h2>
          <ul className="flex flex-col">
            {day.items.map((transaction) => {
              const income = transaction.type === 'income'
              const property = properties.get(transaction.property_id)?.name
              return (
                <ListRow
                  key={transaction.id}
                  label={`${sentence(transaction.concept)}, ${money(transaction.amount)}`}
                  onSelect={() => onSelect(transaction)}
                  mark={
                    <MethodMark
                      type={transaction.type}
                      method={transaction.payment_method}
                    />
                  }
                  title={sentence(transaction.concept)}
                  meta={
                    <span className="truncate">
                      {[
                        property,
                        sentence(transaction.payment_method),
                        sentence(transaction.category),
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </span>
                  }
                  trailing={
                    <span className="flex shrink-0 flex-col items-end">
                      <span
                        className={cn(
                          'text-base font-semibold whitespace-nowrap tabular-nums',
                          income
                            ? 'text-emerald-700 dark:text-emerald-500'
                            : 'text-neutral-900 dark:text-neutral-100',
                        )}
                      >
                        {income ? '+' : ''}
                        {money(transaction.amount)}
                      </span>
                      {transaction.affects_balance && !income && (
                        <span className="text-xs text-muted-foreground">
                          From balance
                        </span>
                      )}
                    </span>
                  }
                />
              )
            })}
          </ul>
        </section>
      ))}
    </div>
  )
}

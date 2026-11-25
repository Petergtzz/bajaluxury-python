'use client'

import { House } from 'lucide-react'
import { useRouter } from 'next/navigation'

import { EmptyCard } from '@/components/empty-card'
import { ListHeading, ListRow, RowMark } from '@/components/list-row'
import { PageHeader } from '@/components/page-header'
import { useCurrency, usePermissions } from '@/components/session-context'
import { Spinner } from '@/components/ui/spinner'
import { useBalances } from '@/hooks/ledger'
import { getErrorMessage } from '@/lib/api/errors'
import type { PropertyBalance } from '@/lib/api/types'
import { counted, formatDate, formatMoney } from '@/lib/format'
import { cn } from '@/lib/utils'

/**
 * What each owner has with us, the most owed first. Above the list, what is
 * owed in all: the number this page is opened for.
 */
export function Balances() {
  const { manages } = usePermissions()
  const currency = useCurrency()
  const balances = useBalances()
  const rows = balances.data ?? []
  const owing = rows.filter((row) => row.balance < 0)
  const owed = owing.reduce((total, row) => total + row.balance, 0)

  return (
    <>
      <PageHeader
        title={manages ? 'Balances' : 'Balance'}
        description="Income adds to a balance; only expenses paid from it take away."
      />
      {balances.isPending ? (
        <p className="inline-flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner /> Loading balances
        </p>
      ) : balances.isError ? (
        <p className="text-sm text-destructive">{getErrorMessage(balances.error)}</p>
      ) : rows.length === 0 ? (
        <EmptyCard title="No properties yet">
          Balances show here once there is a property.
        </EmptyCard>
      ) : (
        <>
          {manages && (
            <section
              aria-label="Owed"
              className="rounded-3xl bg-neutral-50 px-6 py-7 sm:px-9 sm:py-8 dark:bg-neutral-800/50"
            >
              <div className="mb-1.5 text-sm text-muted-foreground">Owed to us</div>
              <p className="text-[32px] font-bold tracking-tight whitespace-nowrap tabular-nums sm:text-5xl">
                {formatMoney(-owed, currency)}
              </p>
              <p className="mt-4 text-[15px] text-muted-foreground">
                {counted(owing.length, 'property is', 'properties are')} in the red, of{' '}
                {rows.length}.
              </p>
            </section>
          )}
          <div>
            <ListHeading>{counted(rows.length, 'property', 'properties')}</ListHeading>
            <ul className="flex flex-col">
              {rows.map((row) => (
                <BalanceRow key={row.property_id} row={row} currency={currency} />
              ))}
            </ul>
          </div>
        </>
      )}
    </>
  )
}

function BalanceRow({ row, currency }: { row: PropertyBalance; currency: string }) {
  const router = useRouter()
  return (
    <ListRow
      label={`${row.property_name}, ${formatMoney(row.balance, currency)}`}
      onSelect={() => router.push(`/transactions?property=${row.property_id}&period=all`)}
      mark={
        <RowMark>
          <House className="size-5" strokeWidth={1.8} />
        </RowMark>
      }
      title={row.property_name}
      meta={
        row.last_income_date
          ? `Last paid in ${formatDate(row.last_income_date)}`
          : 'Nothing paid in yet'
      }
      trailing={
        <span
          className={cn(
            'text-base font-semibold whitespace-nowrap tabular-nums',
            row.balance < 0
              ? 'text-destructive'
              : 'text-neutral-900 dark:text-neutral-100',
          )}
        >
          {formatMoney(row.balance, currency)}
        </span>
      }
    />
  )
}

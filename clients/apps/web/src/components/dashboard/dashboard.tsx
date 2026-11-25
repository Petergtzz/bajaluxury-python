'use client'

import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useMemo } from 'react'

import { EmptyCard } from '@/components/empty-card'
import {
  CHIP,
  CHIP_ROW,
  FilterSelect,
  PeriodChip,
} from '@/components/ledger/filter-chips'
import { MethodMark } from '@/components/ledger/method-icon'
import { ListHeading } from '@/components/list-heading'
import { ListRow, RowMark, StatusMeta } from '@/components/list-row'
import { PageHeader } from '@/components/page-header'
import { useCompany, useCurrency } from '@/components/session-context'
import { SummaryCard } from '@/components/summary-card'
import { SelectItem } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { useProperties, useStatement } from '@/hooks/ledger'
import { getErrorMessage } from '@/lib/api/errors'
import type { Statement } from '@/lib/api/types'
import {
  balanceLabel,
  chooseProperty,
  DASHBOARD_PERIODS,
  type DashboardFilters,
  dashboardProperties,
  dashboardRange,
  type ExpenseNarrow,
  expensesHref,
  parseDashboardFilters,
  serializeDashboardFilters,
  share,
} from '@/lib/dashboard/filters'
import { formatMoney, sentence, todayIn } from '@/lib/format'
import { customRange, getPeriodLabel } from '@/lib/period'

/**
 * One house over some days: what it spent, where that went and how it was
 * paid. Two chips choose what is shown; how it was paid is a list rather than
 * a filter, so every method's share is read at once.
 */
export function Dashboard() {
  const company = useCompany()
  const currency = useCurrency()
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const filters = useMemo(() => parseDashboardFilters(searchParams), [searchParams])
  const today = todayIn(company.data?.timezone ?? 'America/Mazatlan')
  const range = dashboardRange(filters, today)

  const properties = useProperties()
  const all = properties.data ?? []
  const property = chooseProperty(all, filters.property)
  const choices = dashboardProperties(all, filters.property)
  const statement = useStatement(property?.id, range)
  const data = statement.data
  const periodLabel = getPeriodLabel(filters.period, today, customRange(filters))

  const setFilters = (patch: Partial<DashboardFilters>) => {
    const address = serializeDashboardFilters({ ...filters, ...patch })
    router.replace(address ? `${pathname}?${address}` : pathname, { scroll: false })
  }

  const header = (
    <PageHeader
      title="Dashboard"
      description="What a house spent, where it went and how it was paid."
    />
  )

  if (properties.isPending || properties.isError || !property) {
    return (
      <>
        {header}
        {properties.isPending ? (
          <p className="inline-flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner /> Loading
          </p>
        ) : properties.isError ? (
          <p className="text-sm text-destructive">{getErrorMessage(properties.error)}</p>
        ) : (
          <EmptyCard title="No properties yet">
            The dashboard shows a house once there is one.
          </EmptyCard>
        )}
      </>
    )
  }

  return (
    <>
      {header}

      <div className={CHIP_ROW}>
        {choices.length > 1 && (
          <FilterSelect
            label="Property"
            value={property.id}
            onChange={(id) => setFilters({ property: id })}
            className={CHIP}
          >
            {choices.map((one) => (
              <SelectItem key={one.id} value={one.id}>
                {one.name}
              </SelectItem>
            ))}
          </FilterSelect>
        )}
        <PeriodChip
          key={`${filters.from}${filters.to}`}
          period={filters.period}
          custom={customRange(filters)}
          allowed={DASHBOARD_PERIODS.allowed}
          onChange={(period, custom) =>
            setFilters({ period, from: custom?.from ?? '', to: custom?.to ?? '' })
          }
        />
      </div>

      <SummaryCard
        label={`Spent · ${periodLabel}`}
        headline={data && formatMoney(data.expense_total, currency)}
        figures={[
          {
            label: 'Paid from the balance',
            value: data && formatMoney(data.balance_expense_total, currency),
          },
          {
            label: 'Money in',
            value: data && (
              <span className="text-emerald-700 dark:text-emerald-500">
                +{formatMoney(data.income_total, currency)}
              </span>
            ),
          },
          {
            label: balanceLabel(range, today),
            value: data && formatMoney(data.closing_balance, currency),
          },
        ]}
      />

      {statement.isError ? (
        <p className="text-sm text-destructive">{getErrorMessage(statement.error)}</p>
      ) : !data ? null : data.expense_total === 0 ? (
        <EmptyCard title={`Nothing spent · ${periodLabel}`}>
          Expenses recorded for {property.name} show here.
        </EmptyCard>
      ) : (
        <Breakdown
          statement={data}
          currency={currency}
          hrefFor={(narrow) => expensesHref(filters, property.id, narrow)}
          onOpen={(href) => router.push(href)}
        />
      )}
    </>
  )
}

function Breakdown({
  statement,
  currency,
  hrefFor,
  onOpen,
}: {
  statement: Statement
  currency: string
  hrefFor: (narrow: ExpenseNarrow) => string
  onOpen: (href: string) => void
}) {
  const total = statement.expense_total
  // Whether an expense came off the balance was settled when it was recorded,
  // so it is read from the entries, not from what the house pays today.
  const fromBalance = new Set(
    statement.entries
      .filter((entry) => entry.type === 'expense' && entry.affects_balance)
      .map((entry) => entry.payment_method),
  )
  return (
    <>
      <section aria-label="Where it went">
        <ListHeading>Where it went</ListHeading>
        <ul className="flex flex-col">
          {statement.expenses_by_category.map((row) => (
            <ListRow
              key={row.category}
              label={`${sentence(row.category)}, ${formatMoney(row.total, currency)}`}
              onSelect={() => onOpen(hrefFor({ category: row.category }))}
              mark={
                <RowMark className="text-sm font-semibold tabular-nums">
                  {share(row.total, total)}
                </RowMark>
              }
              title={sentence(row.category)}
              meta={
                // The bar is the share in the mark, drawn: the long ones stand out
                // before a single figure is read.
                <span className="flex h-1.5 w-full max-w-60" aria-hidden>
                  <span
                    className="rounded-full bg-neutral-800 dark:bg-neutral-300"
                    style={{ width: `${Math.max((row.total / total) * 100, 1.5)}%` }}
                  />
                </span>
              }
              trailing={
                <span className="shrink-0 text-base font-semibold whitespace-nowrap tabular-nums">
                  {formatMoney(row.total, currency)}
                </span>
              }
            />
          ))}
        </ul>
      </section>

      <section aria-label="How it was paid">
        <ListHeading>How it was paid</ListHeading>
        <ul className="flex flex-col">
          {statement.expenses_by_method.map((row) => {
            const method = row.payment_method
            return (
              <ListRow
                key={method ?? 'none'}
                label={`${sentence(method) || 'No method'}, ${formatMoney(row.total, currency)}`}
                onSelect={method ? () => onOpen(hrefFor({ method })) : undefined}
                mark={<MethodMark type="expense" method={method} />}
                title={sentence(method) || 'No method'}
                meta={
                  <StatusMeta tone={fromBalance.has(method) ? 'on' : 'off'}>
                    {fromBalance.has(method) ? 'From balance' : 'Paid apart'}
                  </StatusMeta>
                }
                trailing={
                  <span className="shrink-0 text-base font-semibold whitespace-nowrap tabular-nums">
                    {formatMoney(row.total, currency)}
                  </span>
                }
              />
            )
          })}
        </ul>
      </section>
    </>
  )
}

'use client'

import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useMemo } from 'react'

import { EmptyCard } from '@/components/empty-card'
import { CHIP, CHIP_ROW, FilterSelect } from '@/components/ledger/filter-chips'
import { MethodMark } from '@/components/ledger/method-icon'
import { ListHeading } from '@/components/list-heading'
import { ListRow, RowMark } from '@/components/list-row'
import { PageHeader } from '@/components/page-header'
import { useCompany, useMoney } from '@/components/session-context'
import { SummaryCard } from '@/components/summary-card'
import { SelectItem } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { useBalances, useProperties, useStatement } from '@/hooks/ledger'
import { getErrorMessage } from '@/lib/api/errors'
import {
  chooseProperty,
  type DashboardFilters,
  dashboardProperties,
  type ExpenseNarrow,
  expensesHref,
  monthLabel,
  monthName,
  monthRange,
  monthsOf,
  parseDashboardFilters,
  serializeDashboardFilters,
  share,
  shownMonth,
} from '@/lib/dashboard/filters'
import { sentence, todayIn } from '@/lib/format'

import { categoryIcon } from './category-icon'

/**
 * One house: what it has with us today, then one month of it. Every figure is
 * an amount with a short name, and every row opens the expenses behind it.
 */
export function Dashboard() {
  const company = useCompany()
  const money = useMoney()
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const filters = useMemo(() => parseDashboardFilters(searchParams), [searchParams])
  const today = todayIn(company.data?.timezone ?? 'America/Mazatlan')

  const properties = useProperties()
  const balances = useBalances({ all: true })
  const all = properties.data ?? []
  const property = chooseProperty(all, filters.property)
  const choices = dashboardProperties(all, filters.property)
  const balance = balances.data?.find((row) => row.property_id === property?.id)
  const month = shownMonth(filters, today)
  const statement = useStatement(property?.id, monthRange(month))
  const data = statement.data

  const setFilters = (patch: Partial<DashboardFilters>) => {
    const address = serializeDashboardFilters({ ...filters, ...patch })
    router.replace(address ? `${pathname}?${address}` : pathname, { scroll: false })
  }
  const open = (narrow: ExpenseNarrow) =>
    property && router.push(expensesHref(month, today, property.id, narrow))

  const header = <PageHeader title="Dashboard" />

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
          <EmptyCard title="No properties yet" />
        )}
      </>
    )
  }

  const spent = data?.expense_total ?? 0

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
        <FilterSelect
          label="Month"
          value={month}
          onChange={(chosen) =>
            setFilters({ month: chosen === today.slice(0, 7) ? '' : chosen })
          }
          className={CHIP}
        >
          {monthsOf(balance?.first_activity_date, today).map((one) => (
            <SelectItem key={one} value={one}>
              {monthLabel(one)}
            </SelectItem>
          ))}
        </FilterSelect>
      </div>

      <SummaryCard
        label="Balance today"
        headline={
          balance && (
            <span className={balance.balance < 0 ? 'text-destructive' : undefined}>
              {money(balance.balance)}
            </span>
          )
        }
        figures={[
          {
            label: 'Received',
            value: data && (
              <span className="text-emerald-700 dark:text-emerald-500">
                +{money(data.income_total)}
              </span>
            ),
          },
          { label: `Spent in ${monthName(month)}`, value: data && money(spent) },
        ]}
      />

      {statement.isError ? (
        <p className="text-sm text-destructive">{getErrorMessage(statement.error)}</p>
      ) : !data ? null : spent === 0 ? (
        <EmptyCard title={`Nothing spent in ${monthLabel(month)}`} />
      ) : (
        <>
          <section aria-label="Spent by payment method">
            <ListHeading>Spent by payment method</ListHeading>
            <ul className="flex flex-col">
              {data.expenses_by_method.map((row) => {
                const method = row.payment_method
                const name = sentence(method) || 'No method'
                return (
                  <ListRow
                    key={method ?? 'none'}
                    label={`${name}, ${money(row.total)}`}
                    onSelect={method ? () => open({ method }) : undefined}
                    mark={<MethodMark type="expense" method={method} />}
                    title={name}
                    trailing={<Amount value={money(row.total)} />}
                  />
                )
              })}
            </ul>
          </section>

          <section aria-label="Where it went">
            <ListHeading>Where it went</ListHeading>
            <ul className="flex flex-col">
              {data.expenses_by_category.map((row) => {
                const Icon = categoryIcon(row.category)
                return (
                  <ListRow
                    key={row.category}
                    label={`${sentence(row.category)}, ${money(row.total)}`}
                    onSelect={() => open({ category: row.category })}
                    mark={
                      <RowMark>
                        <Icon className="size-5" strokeWidth={1.8} aria-hidden />
                      </RowMark>
                    }
                    title={sentence(row.category)}
                    trailing={
                      <Amount value={money(row.total)} under={share(row.total, spent)} />
                    }
                  />
                )
              })}
            </ul>
          </section>
        </>
      )}
    </>
  )
}

/** A row's amount, with what it is of the whole in small type under it. */
function Amount({ value, under }: { value: string; under?: string }) {
  return (
    <span className="flex shrink-0 flex-col items-end">
      <span className="text-base font-semibold whitespace-nowrap tabular-nums">
        {value}
      </span>
      {under && (
        <span className="text-xs text-muted-foreground tabular-nums">{under}</span>
      )}
    </span>
  )
}

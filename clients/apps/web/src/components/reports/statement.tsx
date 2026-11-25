'use client'

import { Tag } from 'lucide-react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useMemo, useState } from 'react'

import { EmptyCard } from '@/components/empty-card'
import { CHIP, FilterSelect, PeriodChip } from '@/components/ledger/filter-chips'
import { MethodMark } from '@/components/ledger/method-icon'
import { ListHeading, ListRow, RowMark } from '@/components/list-row'
import { PageHeader } from '@/components/page-header'
import { useCompany } from '@/components/session-context'
import { SummaryCard } from '@/components/summary-card'
import { TabPills } from '@/components/tab-pills'
import { SelectItem } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { useProperties } from '@/hooks/ledger'
import { useStatement } from '@/hooks/reports'
import { getErrorMessage } from '@/lib/api/errors'
import type { schemas } from '@/lib/api/client'
import {
  counted,
  formatDayHeading,
  formatMoney,
  formatRange,
  groupConsecutive,
  sentence,
  todayIn,
} from '@/lib/format'
import { customRange } from '@/lib/period'
import {
  CURRENCIES,
  parseStatementFilters,
  reportRange,
  serializeStatementFilters,
  STATEMENT_PERIODS,
  type StatementFilters,
  toQueryString,
} from '@/lib/reports/filters'
import { cn } from '@/lib/utils'

import { Downloads } from './downloads'

type Statement = schemas['Statement']

const VIEWS = ['entries', 'categories'] as const
type View = (typeof VIEWS)[number]
const VIEW_NAMES: Record<View, string> = { entries: 'Entries', categories: 'By category' }

/**
 * A property's statement: the balance it ended on, how it got there, and
 * the same as a PDF or a sheet, exactly as the owner receives it.
 */
export function StatementReport() {
  const company = useCompany()
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const filters = useMemo(() => parseStatementFilters(searchParams), [searchParams])
  const today = todayIn(company.data?.timezone ?? 'America/Mazatlan')
  const properties = useProperties()
  const active = (properties.data ?? []).filter(
    (property) => !property.is_archived || property.id === filters.property,
  )
  // A statement is always about one property: the first, until one is chosen.
  const propertyId = filters.property || active[0]?.id || ''
  const range = reportRange(filters, today, STATEMENT_PERIODS)
  const query = { ...range, ...(filters.currency && { currency: filters.currency }) }
  const statement = useStatement(propertyId, query)
  const [view, setView] = useState<View>('entries')

  const setFilters = (patch: Partial<StatementFilters>) => {
    const address = serializeStatementFilters({ ...filters, ...patch })
    router.replace(address ? `${pathname}?${address}` : pathname, { scroll: false })
  }

  const data = statement.data
  const currency = data?.currency ?? filters.currency ?? company.data?.currency ?? 'MXN'
  const files = `/v1/properties/${propertyId}/statement`
  const fileQuery = toQueryString(query)

  return (
    <>
      <PageHeader title="Statement" />

      <div className="no-scrollbar flex items-center gap-2 max-sm:-mx-4 max-sm:px-4">
        {active.length > 1 && (
          <FilterSelect
            label="Property"
            value={propertyId}
            onChange={(property) => setFilters({ property })}
            className={CHIP}
          >
            {active.map((property) => (
              <SelectItem key={property.id} value={property.id}>
                {property.name}
              </SelectItem>
            ))}
          </FilterSelect>
        )}
        <PeriodChip
          key={`${filters.from}${filters.to}`}
          period={filters.period}
          custom={customRange(filters)}
          allowed={STATEMENT_PERIODS.allowed}
          onChange={(period, custom) =>
            setFilters({ period, from: custom?.from ?? '', to: custom?.to ?? '' })
          }
        />
        <FilterSelect
          label="Currency"
          value={filters.currency || company.data?.currency || 'MXN'}
          onChange={(value) =>
            setFilters({
              currency:
                value === company.data?.currency
                  ? ''
                  : (value as StatementFilters['currency']),
            })
          }
          className={CHIP}
        >
          {CURRENCIES.map((one) => (
            <SelectItem key={one} value={one}>
              {one}
            </SelectItem>
          ))}
        </FilterSelect>
      </div>

      {!propertyId && properties.isSuccess ? (
        <EmptyCard title="No property to report on" />
      ) : (
        <>
          <SummaryCard
            label={
              <>
                Ending balance ·{' '}
                <span className="whitespace-nowrap">
                  {formatRange(range.start, range.end)}
                </span>
              </>
            }
            headline={
              data && <Signed amount={data.closing_balance} currency={currency} />
            }
            corner={
              propertyId && (
                <Downloads
                  pdf={`${files}.pdf?${fileQuery}`}
                  excel={`${files}.xlsx?${fileQuery}`}
                />
              )
            }
            figures={[
              {
                label: 'Previous balance',
                value: data && (
                  <Signed amount={data.opening_balance} currency={currency} />
                ),
              },
              {
                label: 'Income',
                value: data && (
                  <span className="text-emerald-700 dark:text-emerald-500">
                    +{formatMoney(data.income_total, currency)}
                  </span>
                ),
              },
              {
                label: 'Paid from balance',
                value: data && formatMoney(-data.balance_expense_total, currency),
              },
            ]}
          />
          {data?.exchange_rate && (
            <p className="-mt-4 text-sm text-muted-foreground">
              Converted at 1 USD = {Number(data.exchange_rate)} MXN.
            </p>
          )}

          <TabPills
            label="Statement view"
            tabs={VIEWS}
            current={view}
            onSelect={setView}
            labels={VIEW_NAMES}
            counts={{
              entries: data?.entries.length,
              categories: data?.expenses_by_category.length,
            }}
          />

          {statement.isPending ? (
            <p className="inline-flex items-center gap-2 text-sm text-muted-foreground">
              <Spinner /> Loading the statement
            </p>
          ) : statement.isError ? (
            <p className="text-sm text-destructive">{getErrorMessage(statement.error)}</p>
          ) : data && view === 'entries' ? (
            <Entries statement={data} currency={currency} today={today} />
          ) : (
            data && <Categories statement={data} currency={currency} />
          )}
        </>
      )}
    </>
  )
}

/** A balance: red when the owner owes us. */
function Signed({ amount, currency }: { amount: number; currency: string }) {
  return (
    <span className={cn(amount < 0 && 'text-destructive')}>
      {formatMoney(amount, currency)}
    </span>
  )
}

function Entries({
  statement,
  currency,
  today,
}: {
  statement: Statement
  currency: string
  today: string
}) {
  if (statement.entries.length === 0) {
    return <EmptyCard title="Nothing recorded in this period" />
  }
  return (
    <div className="flex flex-col gap-9">
      {groupConsecutive(statement.entries, (entry) => entry.date).map((day) => (
        <section key={day.key} aria-label={formatDayHeading(day.key, today)}>
          <ListHeading>{formatDayHeading(day.key, today)}</ListHeading>
          <ul className="flex flex-col">
            {day.items.map((entry) => {
              const income = entry.type === 'income'
              return (
                <ListRow
                  key={entry.id}
                  mark={<MethodMark type={entry.type} method={entry.payment_method} />}
                  title={sentence(entry.concept)}
                  meta={
                    <span className="truncate">
                      {[sentence(entry.payment_method), sentence(entry.category)]
                        .filter(Boolean)
                        .join(' · ')}
                    </span>
                  }
                  trailing={
                    <span className="flex shrink-0 flex-col items-end">
                      <span
                        className={cn(
                          'text-base font-semibold whitespace-nowrap tabular-nums',
                          income && 'text-emerald-700 dark:text-emerald-500',
                        )}
                      >
                        {income ? '+' : ''}
                        {formatMoney(entry.amount, currency)}
                      </span>
                      {/* The running balance, where this entry moved it. */}
                      <span
                        className={cn(
                          'text-xs whitespace-nowrap tabular-nums',
                          entry.affects_balance
                            ? entry.balance_after < 0
                              ? 'font-semibold text-destructive'
                              : 'font-semibold text-neutral-700 dark:text-neutral-300'
                            : 'text-muted-foreground',
                        )}
                      >
                        Balance {formatMoney(entry.balance_after, currency)}
                      </span>
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

function Categories({ statement, currency }: { statement: Statement; currency: string }) {
  if (statement.expenses_by_category.length === 0) {
    return <EmptyCard title="No expenses in this period" />
  }
  return (
    <div>
      <ListHeading>
        {formatMoney(statement.expense_total, currency)} in expenses, however they were
        paid
      </ListHeading>
      <ul className="flex flex-col">
        {statement.expenses_by_category.map((category) => {
          const share = statement.expense_total
            ? category.total / statement.expense_total
            : 0
          return (
            <ListRow
              key={category.category}
              mark={
                <RowMark>
                  <Tag className="size-5" strokeWidth={1.8} />
                </RowMark>
              }
              title={sentence(category.category)}
              meta={
                <span className="flex min-w-0 items-center gap-2">
                  <span className="h-1.5 w-24 shrink-0 overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-700">
                    <span
                      className="block h-full rounded-full bg-neutral-900 dark:bg-neutral-100"
                      style={{ width: `${Math.max(share * 100, 2)}%` }}
                    />
                  </span>
                  <span className="truncate">
                    {Math.round(share * 100)}% ·{' '}
                    {counted(category.entries.length, 'entry', 'entries')}
                  </span>
                </span>
              }
              trailing={
                <span className="text-base font-semibold whitespace-nowrap tabular-nums">
                  {formatMoney(category.total, currency)}
                </span>
              }
            />
          )
        })}
      </ul>
    </div>
  )
}

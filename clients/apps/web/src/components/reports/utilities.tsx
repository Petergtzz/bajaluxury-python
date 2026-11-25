'use client'

import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useMemo } from 'react'

import { EmptyCard } from '@/components/empty-card'
import { CHIP, FilterSelect, PeriodChip } from '@/components/ledger/filter-chips'
import { PageHeader } from '@/components/page-header'
import { useCompany } from '@/components/session-context'
import { SummaryCard } from '@/components/summary-card'
import { TabPills } from '@/components/tab-pills'
import { SelectItem } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { useProperties } from '@/hooks/ledger'
import { useBuckets, useUtilities } from '@/hooks/reports'
import { getErrorMessage } from '@/lib/api/errors'
import type { schemas } from '@/lib/api/client'
import { formatMoney, formatRange, todayIn } from '@/lib/format'
import { customRange } from '@/lib/period'
import {
  CURRENCIES,
  parseUtilitiesFilters,
  reportRange,
  serializeUtilitiesFilters,
  toQueryString,
  UTILITIES_PERIODS,
  type UtilitiesFilters,
  type UtilityView,
} from '@/lib/utilities/filters'
import { cn } from '@/lib/utils'

import { Downloads } from './downloads'

type Report = schemas['UtilitiesReport']

const VIEW_NAMES: Record<UtilityView, string> = { totals: 'Totals', tracker: 'Tracker' }

const MONTH = new Intl.DateTimeFormat('en-GB', { month: 'short', year: '2-digit' })
const monthName = (month: string) => {
  const [year = 0, number = 1] = month.split('-').map(Number)
  return MONTH.format(new Date(year, number - 1, 1))
}
const monthInitial = (month: string) => monthName(month).charAt(0)

/**
 * What went to each kind of bill, month by month: the totals, and the
 * tracker, which shows a month a bill was not recorded in at a glance.
 */
export function UtilitiesReportPage() {
  const company = useCompany()
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const filters = useMemo(() => parseUtilitiesFilters(searchParams), [searchParams])
  const today = todayIn(company.data?.timezone ?? 'America/Mazatlan')
  const properties = useProperties()
  const buckets = useBuckets()
  const active = (properties.data ?? []).filter(
    (property) => !property.is_archived || property.id === filters.property,
  )
  const range = reportRange(filters, today, UTILITIES_PERIODS)
  const tracker = filters.view === 'tracker'
  const query = {
    ...range,
    ...(filters.property && { property_id: filters.property }),
    ...(filters.currency && { currency: filters.currency }),
    // The tracker follows every recurring bill, the house staff's too.
    ...(tracker && { buckets: buckets.data?.map((bucket) => bucket.key) }),
  }
  const report = useUtilities(query, !tracker || buckets.isSuccess)

  const setFilters = (patch: Partial<UtilitiesFilters>) => {
    const address = serializeUtilitiesFilters({ ...filters, ...patch })
    router.replace(address ? `${pathname}?${address}` : pathname, { scroll: false })
  }

  const data = report.data
  const currency = data?.currency ?? filters.currency ?? company.data?.currency ?? 'MXN'
  const files = toQueryString(query)
  const months = data?.months.length ?? 0

  return (
    <>
      <PageHeader title="Utilities" />

      <div className="no-scrollbar flex items-center gap-2 max-sm:-mx-4 max-sm:px-4">
        <PeriodChip
          key={`${filters.from}${filters.to}`}
          period={filters.period}
          custom={customRange(filters)}
          allowed={UTILITIES_PERIODS.allowed}
          onChange={(period, custom) =>
            setFilters({ period, from: custom?.from ?? '', to: custom?.to ?? '' })
          }
        />
        {active.length > 1 && (
          <FilterSelect
            label="Property"
            value={filters.property}
            onChange={(property) => setFilters({ property })}
            allLabel="All properties"
            className={CHIP}
          >
            {active.map((property) => (
              <SelectItem key={property.id} value={property.id}>
                {property.name}
              </SelectItem>
            ))}
          </FilterSelect>
        )}
        {!tracker && (
          <FilterSelect
            label="Currency"
            value={filters.currency || company.data?.currency || 'MXN'}
            onChange={(value) =>
              setFilters({
                currency:
                  value === company.data?.currency
                    ? ''
                    : (value as UtilitiesFilters['currency']),
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
        )}
      </div>

      <SummaryCard
        label={
          <>
            {data?.property_name ?? 'All properties'} ·{' '}
            <span className="whitespace-nowrap">
              {formatRange(range.start, range.end)}
            </span>
          </>
        }
        headline={data && formatMoney(data.grand_total, currency)}
        corner={
          !tracker && (
            <Downloads
              pdf={`/v1/reports/utilities.pdf?${files}`}
              excel={`/v1/reports/utilities.xlsx?${files}`}
            />
          )
        }
        figures={[
          {
            label: 'A month, on average',
            value: data && formatMoney(months ? data.grand_total / months : 0, currency),
          },
          {
            label: 'Bills',
            value:
              data &&
              Object.values(data.totals)
                .reduce((total, bucket) => total + bucket.count, 0)
                .toLocaleString('en-US'),
          },
        ]}
      />

      <TabPills
        label="Utilities view"
        tabs={['totals', 'tracker'] as const}
        current={filters.view}
        onSelect={(view) => setFilters({ view })}
        labels={VIEW_NAMES}
      />

      {report.isPending ? (
        <p className="inline-flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner /> Loading the report
        </p>
      ) : report.isError ? (
        <p className="text-sm text-destructive">{getErrorMessage(report.error)}</p>
      ) : !data || data.grand_total === 0 ? (
        <EmptyCard title="No bills in this period" />
      ) : tracker ? (
        <Tracker report={data} thisMonth={today.slice(0, 7)} />
      ) : (
        <Totals report={data} currency={currency} />
      )}
    </>
  )
}

/**
 * Months down, bills across, as the PDF prints it. A wide year scrolls inside
 * its own box, never the page.
 */
function Totals({ report, currency }: { report: Report; currency: string }) {
  const cell = 'px-3 py-3 text-right whitespace-nowrap tabular-nums'
  return (
    <div className="no-scrollbar -mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
      <table className="w-full min-w-max border-collapse text-[15px]">
        <thead>
          <tr className="border-b border-border text-sm text-muted-foreground">
            <th className="py-3 pr-3 text-left font-normal">Month</th>
            {report.buckets.map((bucket) => (
              <th key={bucket.key} className={cn(cell, 'font-normal')}>
                {bucket.label}
              </th>
            ))}
            <th className={cn(cell, 'pr-0 font-normal')}>Total</th>
          </tr>
        </thead>
        <tbody>
          {report.months.map((month) => (
            <tr key={month.month} className="border-b border-border/60">
              <td className="py-3 pr-3 font-semibold whitespace-nowrap">
                {monthName(month.month)}
              </td>
              {report.buckets.map((bucket) => {
                const value = month.buckets[bucket.key]
                return (
                  <td
                    key={bucket.key}
                    className={cn(cell, !value?.count && 'text-muted-foreground')}
                  >
                    {value?.count ? formatMoney(value.total, currency) : '–'}
                  </td>
                )
              })}
              <td className={cn(cell, 'pr-0 font-semibold')}>
                {formatMoney(month.total, currency)}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="font-bold">
            <td className="py-3 pr-3">Total</td>
            {report.buckets.map((bucket) => (
              <td key={bucket.key} className={cell}>
                {formatMoney(report.totals[bucket.key]?.total ?? 0, currency)}
              </td>
            ))}
            <td className={cn(cell, 'pr-0')}>
              {formatMoney(report.grand_total, currency)}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  )
}

/**
 * Each bill against each month: a filled square for every month it was
 * recorded in, with how many times; a dashed one is a month it is missing
 * from. Months still to come are only faint: nothing is missing from them yet.
 */
function Tracker({ report, thisMonth }: { report: Report; thisMonth: string }) {
  return (
    <div className="flex flex-col">
      <div className="flex items-center border-b border-border pb-3 text-sm text-muted-foreground max-sm:hidden">
        <span className="w-40 shrink-0">Bill</span>
        <Months report={report} render={(month) => monthInitial(month)} />
      </div>
      {report.buckets.map((bucket) => (
        <div
          key={bucket.key}
          className="flex flex-col gap-2 border-b border-border/60 py-3 sm:flex-row sm:items-center"
        >
          <span className="shrink-0 font-semibold sm:w-40">
            {bucket.label}
            <span className="ml-2 text-sm font-normal text-muted-foreground sm:hidden">
              {report.totals[bucket.key]?.count ?? 0} recorded
            </span>
          </span>
          <Months
            report={report}
            render={(month) => {
              const count =
                report.months.find((one) => one.month === month)?.buckets[bucket.key]
                  ?.count ?? 0
              const future = month > thisMonth
              return (
                <span
                  title={`${monthName(month)}: ${count}`}
                  className={cn(
                    'flex size-full items-center justify-center rounded-md text-xs font-semibold tabular-nums',
                    count
                      ? 'bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900'
                      : future
                        ? 'bg-neutral-100 dark:bg-neutral-800/60'
                        : 'border border-dashed border-neutral-300 dark:border-neutral-600',
                  )}
                >
                  {count || ''}
                  {!count && (
                    <span className="sr-only">
                      {future
                        ? `${monthName(month)} is still to come`
                        : `none in ${monthName(month)}`}
                    </span>
                  )}
                </span>
              )
            }}
          />
        </div>
      ))}
    </div>
  )
}

/** The months as a row of small squares, spread across the width left. */
function Months({
  report,
  render,
}: {
  report: Report
  render: (month: string) => React.ReactNode
}) {
  return (
    <span
      className="grid flex-1 grid-cols-[repeat(var(--months),minmax(0,1.75rem))] justify-between gap-1 sm:grid-cols-[repeat(var(--months),minmax(0,2rem))]"
      style={{ '--months': report.months.length } as React.CSSProperties}
    >
      {report.months.map((month) => (
        <span
          key={month.month}
          className="flex aspect-square min-w-0 items-center justify-center"
        >
          {render(month.month)}
        </span>
      ))}
    </span>
  )
}

import { formatRange } from '@/lib/format'

/** The spans of time a list can be narrowed to, all ending where the company is. */
export const PERIODS = ['this-month', 'last-month', 'this-year', 'all', 'custom'] as const
export type Period = (typeof PERIODS)[number]

export const DEFAULT_PERIOD: Period = 'this-month'

export type Range = { from: string; to: string }

const pad = (n: number) => String(n).padStart(2, '0')
const lastDay = (year: number, month: number) => new Date(year, month, 0).getDate()

/** The days a period covers, both included; null for all of them. */
export function getRange(period: Period, today: string, custom?: Range): Range | null {
  const [year = 0, month = 0] = today.split('-').map(Number)
  switch (period) {
    case 'this-month':
      return {
        from: `${year}-${pad(month)}-01`,
        to: `${year}-${pad(month)}-${lastDay(year, month)}`,
      }
    case 'last-month': {
      const [y, m] = month === 1 ? [year - 1, 12] : [year, month - 1]
      return { from: `${y}-${pad(m)}-01`, to: `${y}-${pad(m)}-${lastDay(y, m)}` }
    }
    case 'this-year':
      return { from: `${year}-01-01`, to: `${year}-12-31` }
    case 'custom':
      return custom ?? null
    case 'all':
      return null
  }
}

const MONTH = new Intl.DateTimeFormat('en-GB', { month: 'long', year: 'numeric' })

/** What a period is called over the figures: "November 2026", "2026". */
export function getPeriodLabel(period: Period, today: string, custom?: Range): string {
  const [year = 0, month = 1] = today.split('-').map(Number)
  switch (period) {
    case 'this-month':
      return MONTH.format(new Date(year, month - 1, 1))
    case 'last-month':
      return MONTH.format(new Date(year, month - 2, 1))
    case 'this-year':
      return String(year)
    case 'all':
      return 'All time'
    case 'custom':
      return custom ? formatRange(custom.from, custom.to) : 'Custom'
  }
}

export const PERIOD_NAMES: Record<Period, string> = {
  'this-month': 'This month',
  'last-month': 'Last month',
  'this-year': 'This year',
  all: 'All time',
  custom: 'Custom',
}

/** A period as the address carries it: custom days only with a custom period. */
export type PeriodFilter = { period: Period; from: string; to: string }

const DATE = /^\d{4}-\d{2}-\d{2}$/

/** The period from the address; nonsense, or days that end before they start, is the default. */
export function readPeriod(params: URLSearchParams): PeriodFilter {
  const from = params.get('from') ?? ''
  const to = params.get('to') ?? ''
  const asked = params.get('period')
  const period = PERIODS.includes(asked as Period) ? (asked as Period) : DEFAULT_PERIOD
  const custom = period === 'custom' && DATE.test(from) && DATE.test(to) && from <= to
  if (period === 'custom' && !custom) return { period: DEFAULT_PERIOD, from: '', to: '' }
  return { period, from: custom ? from : '', to: custom ? to : '' }
}

/** Writes the period into the address, leaving it out at its default. */
export function writePeriod(params: URLSearchParams, filter: PeriodFilter): void {
  if (filter.period !== DEFAULT_PERIOD) params.set('period', filter.period)
  if (filter.period === 'custom') {
    params.set('from', filter.from)
    params.set('to', filter.to)
  }
}

export const customRange = (filter: PeriodFilter): Range | undefined =>
  filter.period === 'custom' ? { from: filter.from, to: filter.to } : undefined

/** The API's dates for a period, today being the company's. */
export function periodQuery(filter: PeriodFilter, today: string) {
  const range = getRange(filter.period, today, customRange(filter))
  return range ? { start_date: range.from, end_date: range.to } : {}
}

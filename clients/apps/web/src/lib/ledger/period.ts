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

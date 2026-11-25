import { type PeriodFilter, periodQuery, readPeriod, writePeriod } from '@/lib/period'

export const BILLED = ['billed', 'unbilled'] as const
export type Billed = (typeof BILLED)[number]

/** What narrows the guest expenses, as the address carries it. */
export type GuestExpenseFilters = PeriodFilter & {
  property: string
  billed: Billed | ''
  category: string
}

export function parseGuestExpenseFilters(params: URLSearchParams): GuestExpenseFilters {
  const billed = params.get('billed')
  return {
    ...readPeriod(params),
    property: params.get('property') ?? '',
    billed: BILLED.includes(billed as Billed) ? (billed as Billed) : '',
    category: params.get('category') ?? '',
  }
}

export function serializeGuestExpenseFilters(filters: GuestExpenseFilters): string {
  const params = new URLSearchParams()
  writePeriod(params, filters)
  for (const key of ['property', 'billed', 'category'] as const) {
    if (filters[key]) params.set(key, filters[key])
  }
  return params.toString()
}

export function toGuestExpenseQuery(filters: GuestExpenseFilters, today: string) {
  return {
    ...periodQuery(filters, today),
    ...(filters.property && { property_id: filters.property }),
    ...(filters.billed && { invoiced: filters.billed === 'billed' }),
    ...(filters.category && { category: filters.category }),
  }
}

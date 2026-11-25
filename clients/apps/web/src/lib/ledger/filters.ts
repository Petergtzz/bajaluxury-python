import type { PaymentMethod, TransactionType } from '@/lib/api/types'
import { type PeriodFilter, periodQuery, readPeriod, writePeriod } from '@/lib/period'

/** What narrows the ledger, as the address carries it. */
export type LedgerFilters = PeriodFilter & {
  property: string
  type: TransactionType | ''
  method: PaymentMethod | ''
  category: string
}

const TYPES: readonly TransactionType[] = ['income', 'expense']
export const METHODS: readonly PaymentMethod[] = [
  'cash',
  'credit card',
  'debit card',
  'withdrawal',
  'check',
  'wire',
  'paypal',
]

const oneOf = <T extends string>(value: string | null, allowed: readonly T[]): T | '' =>
  allowed.includes(value as T) ? (value as T) : ''

/** Filters from the address; anything unknown is left out, not trusted. */
export function parseFilters(params: URLSearchParams): LedgerFilters {
  return {
    ...readPeriod(params),
    property: params.get('property') ?? '',
    type: oneOf(params.get('type'), TYPES),
    method: oneOf(params.get('method'), METHODS),
    category: params.get('category') ?? '',
  }
}

/** The address for filters, leaving out whatever is at its default. */
export function serializeFilters(filters: LedgerFilters): string {
  const params = new URLSearchParams()
  writePeriod(params, filters)
  for (const key of ['property', 'type', 'method', 'category'] as const) {
    if (filters[key]) params.set(key, filters[key])
  }
  return params.toString()
}

/** The API's query for filters, today being the company's today. */
export function toTransactionQuery(filters: LedgerFilters, today: string) {
  return {
    ...periodQuery(filters, today),
    ...(filters.property && { property_id: filters.property }),
    ...(filters.type && { type: filters.type }),
    ...(filters.method && { payment_method: filters.method }),
    ...(filters.category && { category: filters.category }),
  }
}

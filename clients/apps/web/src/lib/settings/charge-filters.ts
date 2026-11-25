import type { RecurringCharge } from '@/lib/api/types'

/** Which charges show: what they are for, and which house pays them. Empty is all. */
export type ChargeFilters = { what: string; property: string }

export const parseChargeFilters = (params: URLSearchParams): ChargeFilters => ({
  what: params.get('what') ?? '',
  property: params.get('property') ?? '',
})

/** The address for filters, leaving out whatever is at its default. */
export const serializeChargeFilters = (filters: ChargeFilters): string => {
  const params = new URLSearchParams()
  if (filters.what) params.set('what', filters.what)
  if (filters.property) params.set('property', filters.property)
  return params.toString()
}

/** What a charge is for, as the filter knows it: its concept, whatever its case. */
const kindOf = (charge: RecurringCharge) => charge.concept.trim().toLowerCase()

export const applyChargeFilters = (
  charges: RecurringCharge[],
  filters: ChargeFilters,
): RecurringCharge[] =>
  charges.filter(
    (charge) =>
      (!filters.what || kindOf(charge) === filters.what) &&
      (!filters.property || charge.property_id === filters.property),
  )

/** The kinds of charge there are, the most common first: what the chip offers. */
export const chargeKinds = (
  charges: RecurringCharge[],
): { kind: string; count: number }[] =>
  [...Map.groupBy(charges, kindOf)]
    .map(([kind, items]) => ({ kind, count: items.length }))
    .sort((a, b) => b.count - a.count || a.kind.localeCompare(b.kind))

/** What the charges shown add up to each month, and across how many houses. */
export const summarizeCharges = (charges: RecurringCharge[]) => ({
  monthly:
    charges.reduce((sum, charge) => sum + Math.round(charge.amount * 100), 0) / 100,
  count: charges.length,
  houses: new Set(charges.map((charge) => charge.property_id)).size,
})

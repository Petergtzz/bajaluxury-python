import { describe, expect, it } from 'vitest'

import type { RecurringCharge } from '@/lib/api/types'

import {
  applyChargeFilters,
  chargeKinds,
  parseChargeFilters,
  serializeChargeFilters,
  summarizeCharges,
} from './charge-filters'

const charge = (id: string, property_id: string, concept: string, amount: number) =>
  ({ id, property_id, concept, amount }) as RecurringCharge

const CHARGES = [
  charge('a', 'campo', 'property management', 8500),
  charge('b', 'campo', 'Landscaping', 7000.5),
  charge('c', 'colinas', 'property management', 8500),
  charge('d', 'colinas', 'landscaping ', 1500),
  charge('e', 'colinas', 'starlink', 1305),
]

describe('charge filters', () => {
  it('live in the address, defaults left out', () => {
    const filters = parseChargeFilters(
      new URLSearchParams('what=landscaping&property=campo'),
    )
    expect(filters).toEqual({ what: 'landscaping', property: 'campo' })
    expect(serializeChargeFilters(filters)).toBe('what=landscaping&property=campo')
    expect(serializeChargeFilters({ what: '', property: '' })).toBe('')
  })

  it('keep the charges for one thing, whatever its case, and one house', () => {
    const ids = (what: string, property = '') =>
      applyChargeFilters(CHARGES, { what, property }).map((one) => one.id)
    expect(ids('landscaping')).toEqual(['b', 'd'])
    expect(ids('landscaping', 'colinas')).toEqual(['d'])
    expect(ids('')).toHaveLength(5)
  })

  it('offer the kinds there are, the most common first', () => {
    expect(chargeKinds(CHARGES)).toEqual([
      { kind: 'landscaping', count: 2 },
      { kind: 'property management', count: 2 },
      { kind: 'starlink', count: 1 },
    ])
  })

  it('add up a month to the cent, across the houses shown', () => {
    expect(
      summarizeCharges(
        applyChargeFilters(CHARGES, { what: 'landscaping', property: '' }),
      ),
    ).toEqual({ monthly: 8500.5, count: 2, houses: 2 })
  })
})

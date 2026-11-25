import { describe, expect, it } from 'vitest'

import type { RecurringCharge } from '@/lib/api/types'

import {
  dayName,
  describeCharge,
  draftFromCharge,
  toChargeChanges,
  toChargeCreate,
} from './charges'

const CHARGE: RecurringCharge = {
  id: 'r1',
  property_id: 'p1',
  amount: 1500,
  payment_method: 'debit card',
  category: 'services',
  concept: 'gardener',
  description: null,
  day_of_month: 31,
  next_charge_on: '2026-11-30',
  created_at: '2026-09-01T00:00:00Z',
}

describe('recurring charges', () => {
  it('say what is missing before they are saved', () => {
    expect(toChargeCreate(draftFromCharge(null))).toEqual({
      error: 'Pick the property it is charged to.',
    })
    expect(toChargeCreate({ ...draftFromCharge(CHARGE), amount: '0' })).toEqual({
      error: 'Enter the amount.',
    })
  })

  it('send a new one whole, the typed amount as the API reads it', () => {
    expect(
      toChargeCreate({
        ...draftFromCharge(CHARGE),
        amount: '1,250.50',
        description: ' ',
      }),
    ).toEqual({
      body: {
        property_id: 'p1',
        amount: '1250.50',
        category: 'services',
        concept: 'gardener',
        payment_method: 'debit card',
        day_of_month: 31,
        description: null,
      },
    })
  })

  it('send only what changed for one already charging', () => {
    const draft = draftFromCharge(CHARGE)
    expect(draft.amount).toBe('1,500.00')
    expect(toChargeChanges(draft, CHARGE)).toEqual({ body: {} })
    expect(toChargeChanges({ ...draft, amount: '1600', day: 15 }, CHARGE)).toEqual({
      body: { amount: '1600', day_of_month: 15 },
    })
  })

  it('read as people say them', () => {
    expect([dayName(1), dayName(15), dayName(31)]).toEqual([
      'The 1st',
      'The 15th',
      'Last day',
    ])
    expect(describeCharge(CHARGE)).toBe(
      'Services · Debit card · Last day of the month · next 30 Nov 2026',
    )
  })
})

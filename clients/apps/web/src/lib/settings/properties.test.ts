import { describe, expect, it } from 'vitest'

import type { Property } from '@/lib/api/types'

import {
  describeBalance,
  draftFromProperty,
  toNewPropertyBody,
  toPropertyChanges,
} from './properties'

const PROPERTY: Property = {
  id: 'p1',
  name: 'Colinas 21',
  address: 'Calle 21, Cabo',
  is_archived: false,
  balance_methods: ['cash', 'debit card'],
  created_at: '2026-09-01T00:00:00Z',
}

describe('property drafts', () => {
  it('start blank, paying cash, or from the property', () => {
    expect(draftFromProperty(null)).toEqual({
      name: '',
      address: '',
      balanceMethods: ['cash'],
    })
    expect(draftFromProperty({ ...PROPERTY, address: null })).toEqual({
      name: 'Colinas 21',
      address: '',
      balanceMethods: ['cash', 'debit card'],
    })
  })

  it('require a name', () => {
    expect(toNewPropertyBody({ name: ' ', address: '', balanceMethods: [] })).toEqual({
      error: 'Enter a name.',
    })
    expect(
      toPropertyChanges({ name: '', address: '', balanceMethods: [] }, PROPERTY),
    ).toEqual({
      error: 'Enter a name.',
    })
  })

  it('send everything for a new property, a blank address as null', () => {
    expect(
      toNewPropertyBody({
        name: ' Colinas 30 ',
        address: ' ',
        balanceMethods: ['wire', 'cash'],
      }),
    ).toEqual({
      body: { name: 'Colinas 30', address: null, balance_methods: ['cash', 'wire'] },
    })
  })

  it('send only changes for an existing one', () => {
    const draft = draftFromProperty(PROPERTY)
    expect(toPropertyChanges({ ...draft, address: '' }, PROPERTY)).toEqual({
      body: { address: null },
    })
    // The same methods in another order are no change.
    expect(
      toPropertyChanges({ ...draft, balanceMethods: ['debit card', 'cash'] }, PROPERTY),
    ).toEqual({ body: {} })
    expect(toPropertyChanges({ ...draft, balanceMethods: ['cash'] }, PROPERTY)).toEqual({
      body: { balance_methods: ['cash'] },
    })
  })

  it('say what comes out of the balance', () => {
    expect(describeBalance(['debit card', 'cash'])).toBe('Balance pays cash, debit card')
    expect(describeBalance([])).toBe('No expense comes out of the balance')
  })
})

import { describe, expect, it } from 'vitest'

import type { ManagedUser } from '@/lib/api/types'

import {
  draftFromPerson,
  newPersonDraft,
  personChanges,
  propertiesLabel,
  toPersonBody,
} from './team'

const ANA: ManagedUser = {
  id: 'u2',
  email: 'ana@example.com',
  name: 'Ana Ruiz',
  role: 'homeowner',
  property_ids: ['p1'],
}

describe('people', () => {
  it('need an address to log in with', () => {
    expect(toPersonBody({ ...newPersonDraft(), email: 'ana' })).toEqual({
      error: 'Enter the email address they log in with.',
    })
  })

  it('send houses for a homeowner only', () => {
    expect(
      toPersonBody({
        email: ' luis@example.com ',
        name: ' ',
        role: 'manager',
        propertyIds: ['p1'],
      }),
    ).toEqual({
      body: { email: 'luis@example.com', name: null, role: 'manager', property_ids: [] },
    })
    expect(
      toPersonBody({
        email: 'ana@example.com',
        name: 'Ana',
        role: 'homeowner',
        propertyIds: ['p1'],
      }),
    ).toEqual({
      body: {
        email: 'ana@example.com',
        name: 'Ana',
        role: 'homeowner',
        property_ids: ['p1'],
      },
    })
  })

  it('save only what changed', () => {
    const draft = draftFromPerson(ANA)
    expect(personChanges(ANA, draft)).toEqual({ body: {} })
    expect(
      personChanges(ANA, { ...draft, propertyIds: ['p1', 'p2'], name: 'Ana' }),
    ).toEqual({
      body: { name: 'Ana', property_ids: ['p1', 'p2'] },
    })
    // Made a manager, their houses go with the role, not in the request.
    expect(personChanges(ANA, { ...draft, role: 'manager', propertyIds: [] })).toEqual({
      body: { role: 'manager' },
    })
  })

  it('say which houses someone sees', () => {
    expect(propertiesLabel('manager', [])).toBe('All properties')
    expect(propertiesLabel('homeowner', [])).toBe('No house yet')
    expect(propertiesLabel('homeowner', ['Colinas 21', 'Campo 9'])).toBe(
      'Colinas 21, Campo 9',
    )
  })
})

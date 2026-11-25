import { describe, expect, it } from 'vitest'

import type { ManagedUser, Property } from '@/lib/api/types'

import {
  applyPropertyStatus,
  applyUserFilters,
  parsePropertyStatus,
  parseUserFilters,
  serializePropertyStatus,
  serializeUserFilters,
} from './team-filters'

const person = (id: string, role: ManagedUser['role'], property_ids: string[] = []) =>
  ({ id, role, property_ids }) as ManagedUser

const PEOPLE = [
  person('boss', 'owner'),
  person('luis', 'manager'),
  person('ana', 'homeowner', ['colinas']),
  person('eva', 'homeowner', ['campo', 'colinas']),
  person('bob', 'homeowner', ['campo']),
]

describe('user filters', () => {
  it('live in the address, and ignore a role that isn’t one', () => {
    const filters = parseUserFilters(new URLSearchParams('role=homeowner&property=campo'))
    expect(filters).toEqual({ role: 'homeowner', property: 'campo' })
    expect(serializeUserFilters(filters)).toBe('role=homeowner&property=campo')
    expect(parseUserFilters(new URLSearchParams('role=admin'))).toEqual({
      role: '',
      property: '',
    })
  })

  it('narrow to a role, or to the homeowners of one house', () => {
    const ids = (role: '' | 'manager', property = '') =>
      applyUserFilters(PEOPLE, { role, property }).map((one) => one.id)
    expect(ids('manager')).toEqual(['luis'])
    expect(ids('', 'colinas')).toEqual(['ana', 'eva'])
    expect(ids('')).toHaveLength(5)
  })
})

describe('property status', () => {
  const house = (id: string, is_archived: boolean) => ({ id, is_archived }) as Property
  const HOUSES = [house('campo', false), house('soleil', true)]

  it('starts on the houses managed today, and leaves that out of the address', () => {
    expect(parsePropertyStatus(new URLSearchParams())).toBe('active')
    expect(parsePropertyStatus(new URLSearchParams('status=nonsense'))).toBe('active')
    expect(serializePropertyStatus('active')).toBe('')
    expect(serializePropertyStatus('archived')).toBe('status=archived')
  })

  it('keeps the active, the archived, or every house', () => {
    const ids = (status: 'active' | 'archived' | 'all') =>
      applyPropertyStatus(HOUSES, status).map((one) => one.id)
    expect([ids('active'), ids('archived'), ids('all')]).toEqual([
      ['campo'],
      ['soleil'],
      ['campo', 'soleil'],
    ])
  })
})

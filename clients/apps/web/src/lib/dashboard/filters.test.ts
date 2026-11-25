import { describe, expect, it } from 'vitest'

import type { Property } from '@/lib/api/types'

import {
  chooseProperty,
  dashboardProperties,
  expensesHref,
  monthLabel,
  monthRange,
  monthsOf,
  parseDashboardFilters,
  serializeDashboardFilters,
  share,
  shownMonth,
} from './filters'

const house = (id: string, name: string, is_archived = false): Property => ({
  id,
  name,
  address: null,
  is_archived,
  balance_methods: ['cash'],
  created_at: '2026-09-01T00:00:00Z',
})
const SOLD = house('p0', 'Acacia', true)
const COLINAS = house('p1', 'Colinas 21')
const CAMPO = house('p2', 'Campo 9')
const TODAY = '2026-11-25'

const parse = (address: string) => parseDashboardFilters(new URLSearchParams(address))

describe('the address', () => {
  it('leaves this month and the first house out', () => {
    expect(parse('')).toEqual({ property: '', month: '' })
    expect(serializeDashboardFilters(parse(''))).toBe('')
    expect(serializeDashboardFilters({ property: 'p1', month: '2026-07' })).toBe(
      'property=p1&month=2026-07',
    )
  })

  it('shows this month for a month that is not one, or is still to come', () => {
    expect(shownMonth(parse('month=2026-13'), TODAY)).toBe('2026-11')
    expect(shownMonth(parse('month=2027-01'), TODAY)).toBe('2026-11')
    expect(shownMonth(parse('month=2026-07'), TODAY)).toBe('2026-07')
  })
})

describe('the house shown', () => {
  it('is the one asked for, else the first in use by name', () => {
    const all = [SOLD, COLINAS, CAMPO]
    expect(chooseProperty(all, '')?.name).toBe('Campo 9')
    expect(chooseProperty(all, 'gone')?.name).toBe('Campo 9')
    expect(chooseProperty(all, 'p0')?.name).toBe('Acacia')
    expect(chooseProperty([SOLD], '')).toBeUndefined()
  })

  it('is picked among those in use, and an archived one only once asked for', () => {
    const names = (asked: string) =>
      dashboardProperties([SOLD, COLINAS, CAMPO], asked).map((p) => p.name)
    expect(names('')).toEqual(['Campo 9', 'Colinas 21'])
    expect(names('p0')).toEqual(['Acacia', 'Campo 9', 'Colinas 21'])
  })
})

describe('the months', () => {
  it('run from the first entry to today, newest first, across a year', () => {
    expect(monthsOf('2025-11-20', TODAY)).toEqual([
      '2026-11',
      '2026-10',
      '2026-09',
      '2026-08',
      '2026-07',
      '2026-06',
      '2026-05',
      '2026-04',
      '2026-03',
      '2026-02',
      '2026-01',
      '2025-12',
      '2025-11',
    ])
  })

  it('are this one alone for a house with nothing yet', () => {
    expect(monthsOf(null, TODAY)).toEqual(['2026-11'])
    expect(monthsOf('2027-02-01', TODAY)).toEqual(['2026-11'])
  })

  it('read as their days and their name', () => {
    expect(monthRange('2028-02')).toEqual({ from: '2028-02-01', to: '2028-02-29' })
    expect(monthLabel('2026-07')).toBe('July 2026')
  })
})

describe('a row', () => {
  it('opens its expenses for the same house and month', () => {
    expect(expensesHref('2026-11', TODAY, 'p1', { category: 'services' })).toBe(
      '/transactions?property=p1&type=expense&category=services',
    )
    expect(expensesHref('2026-10', TODAY, 'p1', { method: 'credit card' })).toBe(
      '/transactions?period=last-month&property=p1&type=expense&method=credit+card',
    )
    expect(expensesHref('2026-07', TODAY, 'p1', { category: 'staff' })).toBe(
      '/transactions?period=custom&from=2026-07-01&to=2026-07-31&property=p1&type=expense&category=staff',
    )
  })

  it('rounds its share, never calling a sliver nothing', () => {
    expect([share(1, 3), share(1, 1000), share(0, 10), share(5, 0)]).toEqual([
      '33%',
      '<1%',
      '0%',
      '0%',
    ])
  })
})

import { expect, it } from 'vitest'

import {
  parseGuestExpenseFilters,
  serializeGuestExpenseFilters,
  toGuestExpenseQuery,
} from './filters'

const parse = (address: string) => parseGuestExpenseFilters(new URLSearchParams(address))

it('reads and writes the address, defaults left out', () => {
  const filters = parse(
    'period=last-month&property=p1&billed=unbilled&category=transport',
  )
  expect(serializeGuestExpenseFilters(filters)).toBe(
    'period=last-month&property=p1&billed=unbilled&category=transport',
  )
  expect(serializeGuestExpenseFilters(parse('billed=maybe'))).toBe('')
})

it('asks the API for billed or not as a yes or no', () => {
  expect(toGuestExpenseQuery(parse('billed=billed&period=all'), '2026-11-25')).toEqual({
    invoiced: true,
  })
  expect(toGuestExpenseQuery(parse('billed=unbilled'), '2026-11-25')).toEqual({
    start_date: '2026-11-01',
    end_date: '2026-11-30',
    invoiced: false,
  })
})

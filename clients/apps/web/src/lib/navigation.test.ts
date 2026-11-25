import { expect, it } from 'vitest'

import { getNavSections } from './navigation'

it('folds the ledgers under Activity, for everyone', () => {
  const [activity] = getNavSections({ manages: false })
  expect(activity?.items?.map((item) => item.href)).toEqual([
    '/transactions',
    '/guest-expenses',
  ])
})

it('names the balances page for who reads it', () => {
  const titles = (manages: boolean) => getNavSections({ manages }).map((s) => s.title)
  expect(titles(true)).toContain('Balances')
  expect(titles(false)).toContain('Balance')
})

it('makes Reports one page, with nothing folded under it', () => {
  const reports = getNavSections({ manages: false }).find((s) => s.title === 'Reports')
  expect(reports?.href).toBe('/reports')
  expect(reports?.items).toBeUndefined()
})

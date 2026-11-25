import { expect, it } from 'vitest'

import { getNavSections } from './navigation'

it('names the balances page for who reads it', () => {
  const titles = (manages: boolean) => getNavSections({ manages }).map((s) => s.title)
  expect(titles(true)).toContain('Balances')
  expect(titles(false)).toContain('Balance')
})

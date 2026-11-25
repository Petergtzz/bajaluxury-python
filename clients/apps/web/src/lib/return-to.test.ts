import { expect, it } from 'vitest'

import { getSafeReturnTo } from './return-to'

it('goes back only to a page on this site', () => {
  expect(getSafeReturnTo('/balances?x=1')).toBe('/balances?x=1')
  expect(getSafeReturnTo('//evil.example')).toBe('/')
  expect(getSafeReturnTo('/\\evil.example')).toBe('/')
  expect(getSafeReturnTo('https://evil.example')).toBe('/')
  expect(getSafeReturnTo(null)).toBe('/')
})

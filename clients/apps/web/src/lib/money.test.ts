import { expect, it } from 'vitest'

import { toShown } from './money'

const MXN = { company: 'MXN', shown: 'MXN', usdRate: 17.2 } as const
const USD = { ...MXN, shown: 'USD' } as const

it('leaves the books alone for those who read them as kept', () => {
  expect(toShown(1250.5, MXN)).toBe(1250.5)
})

it('turns pesos into dollars at the company rate, to the cent', () => {
  expect(toShown(172, USD)).toBe(10)
  expect(toShown(100, USD)).toBe(5.81)
  expect(toShown(-100, USD)).toBe(-5.81)
  expect(toShown(0.086, { ...USD, usdRate: 1 })).toBe(0.09)
})

it('turns dollars into pesos for a company that keeps dollars', () => {
  expect(toShown(10, { company: 'USD', shown: 'MXN', usdRate: 17.2 })).toBe(172)
})

import { describe, expect, it } from 'vitest'

import type { GuestExpense } from '@/lib/api/types'

import { blankLine, lineFor, lineProblem, toLinesBody, totals } from './invoices'

const line = (quantity: string, unitPrice: string) => ({
  ...blankLine(),
  description: 'Cleaning',
  quantity,
  unitPrice,
})

describe('invoice totals', () => {
  it('rounds each line and the tax half up, to the cent, as the server does', () => {
    // 1.5 × 0.33 is 0.495, which floating point makes 0.49499...
    expect(totals([line('1.5', '0.33')])).toEqual({
      subtotal: 0.5,
      tax: 0.08,
      total: 0.58,
    })
    expect(totals([line('1', '1500'), line('2', '1,250.50')])).toEqual({
      subtotal: 4001,
      tax: 640.16,
      total: 4641.16,
    })
    expect(totals([])).toEqual({ subtotal: 0, tax: 0, total: 0 })
  })

  it('says what a line is missing before it is sent', () => {
    expect(lineProblem({ ...line('1', '10'), description: ' ' })).toBe(
      'Every line needs a description.',
    )
    expect(lineProblem(line('0', '10'))).toBe('Every quantity is more than nothing.')
    expect(lineProblem(line('1', ''))).toBe('Every line needs a price.')
    expect(lineProblem(line('1', '0'))).toBeUndefined()
  })

  it('bills a guest expense at what it cost, tied to it', () => {
    const expense = {
      id: 'g1',
      amount: 1500,
      concept: 'costco',
      description: 'groceries before arrival',
    } as GuestExpense
    expect(toLinesBody([lineFor(expense)])).toEqual([
      {
        description: 'Groceries before arrival',
        quantity: 1,
        unit_price: 1500,
        guest_expense_id: 'g1',
      },
    ])
  })
})

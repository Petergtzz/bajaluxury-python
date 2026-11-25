import { screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'

import { OWNER } from '@/test/fixtures'
import { renderSignedIn, stubRoutes } from '@/test/render'

import { AmountField } from './dialog-fields'

afterEach(() => vi.unstubAllGlobals())

const COMPANY = {
  '/v1/company': {
    status: 200,
    body: {
      name: 'Baja Luxury',
      currency: 'MXN',
      timezone: 'America/Mazatlan',
      usd_exchange_rate: '17.2000',
    },
  },
}

it('shows someone who reads dollars what the pesos they type come to', async () => {
  stubRoutes(COMPANY)
  renderSignedIn(<AmountField currency="MXN" value="1,720" readOnly />, {
    ...OWNER,
    display_currency: 'USD',
  })

  expect(await screen.findByText('MXN · ≈ US$100.00')).toBeTruthy()
})

it('adds nothing for someone who reads the books as kept', async () => {
  stubRoutes(COMPANY)
  renderSignedIn(<AmountField currency="MXN" value="1,720" readOnly />)

  await new Promise((resolve) => setTimeout(resolve, 50))
  expect(screen.getByText('MXN')).toBeTruthy()
})

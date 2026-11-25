import type { Metadata } from 'next'
import { Suspense } from 'react'

import { GuestExpenses } from '@/components/guest-expenses/guest-expenses'

export const metadata: Metadata = { title: 'Guest expenses' }

export default function GuestExpensesPage() {
  // The filters are read from the address, which only exists in the browser.
  return (
    <Suspense>
      <GuestExpenses />
    </Suspense>
  )
}

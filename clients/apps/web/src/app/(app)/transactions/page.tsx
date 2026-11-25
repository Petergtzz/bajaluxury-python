import type { Metadata } from 'next'
import { Suspense } from 'react'

import { Ledger } from '@/components/ledger/ledger'

export const metadata: Metadata = { title: 'Transactions' }

export default function TransactionsPage() {
  // The filters are read from the address, which only exists in the browser.
  return (
    <Suspense>
      <Ledger />
    </Suspense>
  )
}

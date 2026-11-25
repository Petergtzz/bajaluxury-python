import type { Metadata } from 'next'
import { Suspense } from 'react'

import { Dashboard } from '@/components/dashboard/dashboard'

export const metadata: Metadata = { title: 'Dashboard' }

export default function DashboardPage() {
  // The filters are read from the address, which only exists in the browser.
  return (
    <Suspense>
      <Dashboard />
    </Suspense>
  )
}

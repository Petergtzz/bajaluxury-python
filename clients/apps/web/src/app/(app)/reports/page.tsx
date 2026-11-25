import type { Metadata } from 'next'
import { Suspense } from 'react'

import { Reports } from '@/components/reports/reports'

export const metadata: Metadata = { title: 'Reports' }

export default function ReportsPage() {
  return (
    <Suspense>
      <Reports />
    </Suspense>
  )
}

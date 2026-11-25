import type { Metadata } from 'next'
import { Suspense } from 'react'

import { UtilitiesReportPage } from '@/components/reports/utilities'

export const metadata: Metadata = { title: 'Utilities' }

export default function UtilitiesPage() {
  return (
    <Suspense>
      <UtilitiesReportPage />
    </Suspense>
  )
}

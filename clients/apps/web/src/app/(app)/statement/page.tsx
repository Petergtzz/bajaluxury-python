import type { Metadata } from 'next'
import { Suspense } from 'react'

import { StatementReport } from '@/components/reports/statement'

export const metadata: Metadata = { title: 'Statement' }

export default function StatementPage() {
  return (
    <Suspense>
      <StatementReport />
    </Suspense>
  )
}

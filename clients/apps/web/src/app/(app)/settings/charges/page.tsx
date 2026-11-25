import type { Metadata } from 'next'
import { Suspense } from 'react'

import { Charges } from '@/components/settings/charges'

export const metadata: Metadata = { title: 'Charges' }

export default function ChargesSettingsPage() {
  return (
    <Suspense>
      <Charges />
    </Suspense>
  )
}

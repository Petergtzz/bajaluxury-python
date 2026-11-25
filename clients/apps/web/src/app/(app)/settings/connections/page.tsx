import type { Metadata } from 'next'
import { Suspense } from 'react'

import { ConnectionsSettings } from '@/components/settings/connections-settings'

export const metadata: Metadata = { title: 'Connections' }

export default function ConnectionsSettingsPage() {
  return (
    <Suspense>
      <ConnectionsSettings />
    </Suspense>
  )
}

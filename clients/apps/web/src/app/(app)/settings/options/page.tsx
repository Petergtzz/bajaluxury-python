import type { Metadata } from 'next'
import { Suspense } from 'react'

import { Options } from '@/components/settings/options'

export const metadata: Metadata = { title: 'Options' }

export default function OptionsSettingsPage() {
  return (
    <Suspense>
      <Options />
    </Suspense>
  )
}

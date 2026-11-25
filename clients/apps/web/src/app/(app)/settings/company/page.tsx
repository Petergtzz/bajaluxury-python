import type { Metadata } from 'next'

import { CompanySettings } from '@/components/settings/company-settings'
import { SettingsPage } from '@/components/settings/settings-layout'

export const metadata: Metadata = { title: 'Company' }

export default function CompanySettingsPage() {
  return (
    <SettingsPage title="Company">
      <CompanySettings />
    </SettingsPage>
  )
}

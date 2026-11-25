import type { Metadata } from 'next'

import { ProfileSettings } from '@/components/settings/profile-settings'
import { SettingsPage } from '@/components/settings/settings-layout'

export const metadata: Metadata = { title: 'Profile' }

export default function ProfileSettingsPage() {
  return (
    <SettingsPage title="Profile">
      <ProfileSettings />
    </SettingsPage>
  )
}

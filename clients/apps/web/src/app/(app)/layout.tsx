import { redirect } from 'next/navigation'
import type { ReactNode } from 'react'

import { AppShell } from '@/components/app-shell'
import { SessionProvider } from '@/components/session-context'
import { getAuthenticatedUser } from '@/lib/api/server'

export default async function SignedInLayout({ children }: { children: ReactNode }) {
  const user = await getAuthenticatedUser()
  // The proxy sends strangers to log in; this is only its backstop.
  if (!user) redirect('/login')
  return (
    <SessionProvider user={user}>
      <AppShell>{children}</AppShell>
    </SessionProvider>
  )
}

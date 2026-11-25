import type { Metadata } from 'next'

import { AuthLayout } from '@/components/auth-layout'

import { EmailForm } from './email-form'

export const metadata: Metadata = { title: 'Log in' }

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ return_to?: string; email?: string }>
}) {
  const { return_to: returnTo, email } = await searchParams
  return (
    <AuthLayout
      title="Log in"
      description="We'll email you a code. There's no password to remember."
    >
      <EmailForm returnTo={returnTo} email={email} />
    </AuthLayout>
  )
}

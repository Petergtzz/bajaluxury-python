import type { Metadata } from 'next'
import { redirect } from 'next/navigation'

import { AuthLayout } from '@/components/auth-layout'

import { CodeForm } from './code-form'

export const metadata: Metadata = { title: 'Enter your code' }

export default async function CodePage({
  searchParams,
}: {
  searchParams: Promise<{ email?: string; return_to?: string }>
}) {
  const { email, return_to: returnTo } = await searchParams
  if (!email) redirect('/login')
  return (
    <AuthLayout
      title="Check your email"
      description={
        <>
          If <span className="font-semibold text-foreground">{email}</span> has an account
          here, a code is on its way.
        </>
      }
    >
      <CodeForm email={email} returnTo={returnTo} />
    </AuthLayout>
  )
}

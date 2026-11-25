import type { ReactNode } from 'react'

import { Logo } from '@/components/brand/logo'

/** The logged-out pages: the logo above one short form in the middle. */
export function AuthLayout({
  title,
  description,
  children,
}: {
  title: string
  description: ReactNode
  children: ReactNode
}) {
  return (
    <main className="flex min-h-screen flex-col items-center px-4 pt-[16vh] pb-16">
      <div className="flex w-full max-w-sm flex-col items-center gap-10">
        <Logo />
        <div className="flex w-full flex-col gap-8">
          <div className="text-center">
            <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
            <p className="mt-2 text-[15px] text-muted-foreground">{description}</p>
          </div>
          {children}
        </div>
      </div>
    </main>
  )
}

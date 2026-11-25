'use client'

import { Menu } from 'lucide-react'
import Link from 'next/link'
import { type ReactNode, useState } from 'react'
import { toast } from 'sonner'

import { AccountButton } from '@/components/account-button'
import { AppSidebar } from '@/components/app-sidebar'
import { Logo } from '@/components/brand/logo'
import { NavDrawer } from '@/components/nav-drawer'
import { usePermissions, useUser } from '@/components/session-context'
import { Button } from '@/components/ui/button'
import { useLogout } from '@/hooks/auth'
import { getErrorMessage } from '@/lib/api/errors'
import { getNavSections } from '@/lib/navigation'

/**
 * Navigation down the left and the page beside it. The sidebar stays put
 * while the page scrolls; below a laptop's width it slides in from a bar.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const user = useUser()
  const permissions = usePermissions()
  const logout = useLogout()
  const [drawerOpen, setDrawerOpen] = useState(false)

  const sidebar = (
    <AppSidebar
      sections={getNavSections(permissions)}
      onNavigate={() => setDrawerOpen(false)}
      account={
        <AccountButton
          user={user}
          onLogout={async () => {
            try {
              await logout.mutateAsync()
            } catch (error) {
              toast.error(getErrorMessage(error))
              return
            }
            // A full load, so the proxy sees the cookie is gone.
            window.location.assign('/login')
          }}
        />
      }
    />
  )

  return (
    <div className="flex min-h-screen w-full">
      <div className="sticky top-0 hidden h-screen w-74 shrink-0 overflow-y-auto lg:block">
        {sidebar}
      </div>
      <NavDrawer open={drawerOpen} onOpenChange={setDrawerOpen}>
        {sidebar}
      </NavDrawer>
      <div className="flex min-w-0 flex-1 flex-col border-border lg:border-l">
        <div className="flex h-14 items-center gap-2 border-b border-border px-2 lg:hidden">
          <Button
            variant="ghost"
            size="icon"
            className="size-10"
            aria-label="Open navigation"
            onClick={() => setDrawerOpen(true)}
          >
            <Menu className="size-5" />
          </Button>
          <Link href="/" aria-label="Baja Luxury" className="px-1">
            <Logo />
          </Link>
        </div>
        <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 px-4 pt-8 pb-14 lg:px-18 lg:pt-10">
          {children}
        </main>
      </div>
    </div>
  )
}

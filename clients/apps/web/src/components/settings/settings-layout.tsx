'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { type ReactNode, useEffect } from 'react'

import { PageHeader, SectionHeader } from '@/components/page-header'
import { usePermissions } from '@/components/session-context'
import { getSettingsTabs } from '@/lib/navigation'
import { cn } from '@/lib/utils'

const isActive = (pathname: string, href: string) =>
  pathname === href || pathname.startsWith(`${href}/`)

/**
 * Settings are one page with a row of tabs, not five pages in the sidebar.
 *
 * They are the corner of the dashboard people visit to change one thing and
 * leave, so they take one line of the navigation and sort themselves out on the
 * page. On a phone the row scrolls sideways.
 *
 * The row holds only the pages this person may change, and a link typed into
 * the bar for one of the others lands on Profile: a homeowner has no business
 * on Charges, and a page of forms that refuse to save is worse than no page.
 */
export function SettingsLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const tabs = getSettingsTabs(usePermissions())
  const allowed = tabs.some((tab) => isActive(pathname, tab.href))
  const profile = '/settings/profile'

  useEffect(() => {
    if (!allowed) {
      router.replace(profile)
    }
  }, [allowed, profile, router])

  if (!allowed) {
    return null
  }

  return (
    <>
      <PageHeader title="Settings" />

      <nav
        aria-label="Settings"
        className="no-scrollbar -mt-2 flex gap-7 overflow-x-auto border-b border-border"
      >
        {tabs.map((tab) => {
          const active = isActive(pathname, tab.href)
          return (
            <Link
              key={tab.href}
              href={tab.href}
              aria-current={active ? 'page' : undefined}
              className={cn(
                'relative shrink-0 pb-3 text-[15px] whitespace-nowrap transition-colors',
                active
                  ? 'font-semibold text-neutral-900 dark:text-neutral-100'
                  : 'font-medium text-muted-foreground hover:text-neutral-900 dark:hover:text-neutral-100',
              )}
            >
              {tab.title}
              {/* Sits on the rule below the row, not under the word. */}
              {active && (
                <span className="absolute -bottom-px left-0 h-0.5 w-full bg-neutral-900 dark:bg-neutral-100" />
              )}
            </Link>
          )
        })}
      </nav>

      {/* Full width: a list fills it, and the forms hold themselves to a
          reading measure. */}
      <div className="min-w-0">{children}</div>
    </>
  )
}

/** One settings page: what it covers, its action, and its fields. */
export function SettingsPage({
  title,
  description,
  actions,
  children,
}: {
  title: string
  description?: ReactNode
  actions?: ReactNode
  children: ReactNode
}) {
  return (
    <section className="flex flex-col gap-8">
      <SectionHeader title={title} description={description} actions={actions} />
      {children}
    </section>
  )
}

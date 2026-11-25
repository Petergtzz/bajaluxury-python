'use client'

import { ChevronDown, ChevronUp } from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import type { ReactNode } from 'react'

import { Logo } from '@/components/brand/logo'
import type { NavLink, NavSection } from '@/lib/navigation'
import { cn } from '@/lib/utils'

const isCurrent = (pathname: string, href: string) =>
  pathname === href || pathname.startsWith(`${href}/`)

const ROW =
  'flex h-12 items-center gap-3.5 rounded-full px-4 transition-colors hover:bg-neutral-100 dark:hover:bg-neutral-800/70'
const CURRENT =
  'bg-neutral-100 font-bold text-neutral-900 dark:bg-neutral-800/70 dark:text-neutral-100'
const OTHER = 'font-medium text-neutral-700 dark:text-neutral-300'

/**
 * The navigation down the left. A section unfolds while one of its pages is
 * showing, and the others stay one line each, so the list reads at a glance.
 */
export function AppSidebar({
  sections,
  account,
  onNavigate,
}: {
  sections: NavSection[]
  account: ReactNode
  /** Closes the drawer on a phone, where the sidebar covers the page. */
  onNavigate?: () => void
}) {
  const pathname = usePathname()
  return (
    <nav aria-label="Main" className="flex h-full flex-col gap-10 px-6 py-10 text-[15px]">
      <Link
        href="/"
        onClick={onNavigate}
        aria-label="Baja Luxury"
        className="self-start px-4"
      >
        <Logo />
      </Link>
      <div className="flex flex-col gap-1">
        {sections.map((section) => (
          <Section
            key={section.title}
            section={section}
            pathname={pathname}
            onNavigate={onNavigate}
          />
        ))}
      </div>
      <div className="mt-auto">{account}</div>
    </nav>
  )
}

function Section({
  section,
  pathname,
  onNavigate,
}: {
  section: NavSection
  pathname: string
  onNavigate?: () => void
}) {
  const items = section.items ?? []
  const open = items.some((item) => isCurrent(pathname, item.href))
  const current = items.length === 0 && isCurrent(pathname, section.href)
  const Chevron = open ? ChevronUp : ChevronDown
  return (
    <>
      <Link
        href={section.href}
        onClick={onNavigate}
        aria-current={current ? 'page' : undefined}
        aria-expanded={items.length > 0 ? open : undefined}
        className={cn(ROW, 'text-base', current ? CURRENT : OTHER)}
      >
        <section.icon className="size-5 shrink-0" strokeWidth={1.8} aria-hidden />
        <span className="flex-1 truncate">{section.title}</span>
        {items.length > 0 && (
          <Chevron className="size-4 shrink-0 text-muted-foreground" aria-hidden />
        )}
      </Link>
      {open && (
        <div className="flex flex-col gap-1 pl-4">
          {items.map((item) => (
            <Item
              key={item.href}
              item={item}
              current={isCurrent(pathname, item.href)}
              onNavigate={onNavigate}
            />
          ))}
        </div>
      )}
    </>
  )
}

function Item({
  item,
  current,
  onNavigate,
}: {
  item: NavLink
  current: boolean
  onNavigate?: () => void
}) {
  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      aria-current={current ? 'page' : undefined}
      className={cn(ROW, 'gap-3', current ? CURRENT : OTHER)}
    >
      <item.icon className="size-[18px] shrink-0" strokeWidth={1.8} aria-hidden />
      <span className="flex-1 truncate">{item.title}</span>
    </Link>
  )
}

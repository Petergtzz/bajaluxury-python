'use client'

import { LogOut, Monitor, Moon, Sun } from 'lucide-react'
import { useTheme } from 'next-themes'

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import type { User } from '@/lib/api/types'
import { cn } from '@/lib/utils'

const initials = (user: { name: string | null; email: string }) =>
  (user.name ?? user.email)
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word.charAt(0).toUpperCase())
    .join('')

/** Someone's initials in a circle: the face of a row about a person. */
export function UserAvatar({
  user,
  className,
}: {
  user: { name: string | null; email: string }
  className?: string
}) {
  return (
    <span
      className={cn(
        'flex size-10 shrink-0 items-center justify-center rounded-full bg-neutral-200 text-sm font-semibold text-black dark:bg-neutral-700 dark:text-white',
        className,
      )}
      aria-hidden
    >
      {initials(user)}
    </span>
  )
}

/** Who is logged in, at the foot of the sidebar; their menu opens from it. */
export function AccountButton({ user, onLogout }: { user: User; onLogout: () => void }) {
  const { setTheme } = useTheme()
  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="flex w-full items-center gap-3 rounded-full p-2 text-left transition-colors outline-none hover:bg-neutral-100 focus-visible:ring-[3px] focus-visible:ring-ring/50 dark:hover:bg-neutral-800/70">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-neutral-900 text-sm font-semibold text-white dark:bg-neutral-100 dark:text-neutral-900">
          {initials(user)}
        </span>
        <span className="min-w-0">
          <span className="block truncate text-sm font-semibold text-neutral-900 dark:text-neutral-100">
            {user.name ?? user.email}
          </span>
          <span className="block truncate text-[13px] text-muted-foreground">
            {user.email}
          </span>
        </span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" side="top" className="w-60">
        <DropdownMenuItem onSelect={() => setTheme('light')}>
          <Sun /> Light
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => setTheme('dark')}>
          <Moon /> Dark
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => setTheme('system')}>
          <Monitor /> Like this device
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={onLogout}>
          <LogOut /> Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

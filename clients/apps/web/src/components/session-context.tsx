'use client'

import { useQuery } from '@tanstack/react-query'
import { createContext, type ReactNode, useContext } from 'react'

import { api, unwrap } from '@/lib/api/client'
import type { User } from '@/lib/api/types'

const UserContext = createContext<User | null>(null)

/** Who is logged in, as the proxy found them for this page. */
export function SessionProvider({ user, children }: { user: User; children: ReactNode }) {
  return <UserContext value={user}>{children}</UserContext>
}

export function useUser(): User {
  const user = useContext(UserContext)
  if (!user) throw new Error('useUser outside a signed-in page')
  return user
}

/**
 * What a role may do, as the API decides it: owners and managers keep the
 * books, homeowners read theirs. The API refuses anyway; this only spares
 * people buttons that can only end in a refusal.
 */
export function usePermissions() {
  const { role } = useUser()
  return {
    manages: role !== 'homeowner',
    ownsCompany: role === 'owner',
  }
}

/** The company: its currency for every amount, its timezone for "today". */
export function useCompany() {
  return useQuery({
    queryKey: ['company'],
    queryFn: () => unwrap(api.GET('/v1/company')),
    staleTime: Infinity,
  })
}

/** The company's currency, MXN until the company has loaded. */
export function useCurrency(): string {
  return useCompany().data?.currency ?? 'MXN'
}

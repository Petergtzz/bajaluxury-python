'use client'

import { useQuery } from '@tanstack/react-query'
import { createContext, type ReactNode, useContext } from 'react'

import { api, unwrap } from '@/lib/api/client'
import type { User } from '@/lib/api/types'
import { formatMoney } from '@/lib/format'
import { toShown } from '@/lib/money'

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

/**
 * The company's currency, MXN until the company has loaded: what amounts are
 * entered in, whatever the reader chose to read them in.
 */
export function useCurrency(): string {
  return useCompany().data?.currency ?? 'MXN'
}

/**
 * Writes an amount from the books as this reader reads it: in the currency
 * they chose, converted at the company's rate. Until the company has loaded
 * there is no rate, so amounts stay in the company's currency.
 */
export function useMoney(): (amount: number) => string {
  const kept = useCurrency()
  const converted = useConverted()
  return converted ?? ((amount) => formatMoney(amount, kept))
}

/**
 * Writes an amount in the reader's currency, or null when they read the
 * company's own: then nothing they see is converted.
 */
export function useConverted(): ((amount: number) => string) | null {
  const company = useCompany().data
  const { display_currency } = useUser()
  if (!company || !display_currency || display_currency === company.currency) return null
  const display = {
    company: company.currency,
    shown: display_currency,
    usdRate: Number(company.usd_exchange_rate),
  }
  return (amount) => formatMoney(toShown(amount, display), display_currency)
}

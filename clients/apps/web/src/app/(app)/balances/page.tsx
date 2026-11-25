import type { Metadata } from 'next'

import { Balances } from '@/components/balances/balances'

export const metadata: Metadata = { title: 'Balances' }

export default function BalancesPage() {
  return <Balances />
}

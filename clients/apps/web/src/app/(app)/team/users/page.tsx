import type { Metadata } from 'next'

import { Users } from '@/components/team/users'

export const metadata: Metadata = { title: 'Users' }

export default function UsersPage() {
  return <Users />
}

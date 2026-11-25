import type { Metadata } from 'next'

import { Checklists } from '@/components/checklists/checklists'

export const metadata: Metadata = { title: 'Checklists' }

export default function ChecklistsPage() {
  return <Checklists />
}

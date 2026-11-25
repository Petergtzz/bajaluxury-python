import type { Metadata } from 'next'

import { ChecklistRun } from '@/components/checklists/checklist-run'

export const metadata: Metadata = { title: 'Checklist' }

export default async function ChecklistPage({
  params,
}: {
  params: Promise<{ checklistId: string }>
}) {
  const { checklistId } = await params
  return <ChecklistRun checklistId={checklistId} />
}

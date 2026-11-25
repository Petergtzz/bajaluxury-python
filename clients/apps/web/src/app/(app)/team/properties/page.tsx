import type { Metadata } from 'next'

import { Properties } from '@/components/team/properties'

export const metadata: Metadata = { title: 'Properties' }

export default function PropertiesPage() {
  return <Properties />
}

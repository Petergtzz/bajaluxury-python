import type { Metadata } from 'next'

import { NewInvoice } from '@/components/invoices/new-invoice'

export const metadata: Metadata = { title: 'New invoice' }

export default function NewInvoicePage() {
  return <NewInvoice />
}

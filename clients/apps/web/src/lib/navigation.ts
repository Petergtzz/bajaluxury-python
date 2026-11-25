import {
  ArrowLeftRight,
  ClipboardCheck,
  FileText,
  type LucideIcon,
  ReceiptText,
  Scale,
  ScrollText,
  WalletCards,
} from 'lucide-react'

export type NavLink = { title: string; href: string; icon: LucideIcon }

export type NavSection = NavLink & {
  /** Pages folded under the section, unfolded while one of them is showing. */
  items?: NavLink[]
}

/** The sidebar, for what someone with these rights may open. */
export function getNavSections({ manages }: { manages: boolean }): NavSection[] {
  return [
    {
      title: 'Activity',
      href: '/transactions',
      icon: ArrowLeftRight,
      items: [
        { title: 'Transactions', href: '/transactions', icon: WalletCards },
        { title: 'Guest expenses', href: '/guest-expenses', icon: ReceiptText },
      ],
    },
    { title: manages ? 'Balances' : 'Balance', href: '/balances', icon: Scale },
    { title: 'Checklists', href: '/checklists', icon: ClipboardCheck },
    // Invoices bill guests, which is the company's business, not a homeowner's.
    ...(manages ? [{ title: 'Invoices', href: '/invoices', icon: ScrollText }] : []),
    { title: 'Reports', href: '/reports', icon: FileText },
  ]
}

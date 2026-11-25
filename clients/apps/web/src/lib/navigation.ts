import { type LucideIcon, Scale, WalletCards } from 'lucide-react'

export type NavLink = { title: string; href: string; icon: LucideIcon }

export type NavSection = NavLink & {
  /** Pages folded under the section, unfolded while one of them is showing. */
  items?: NavLink[]
}

/** The sidebar, for what someone with these rights may open. */
export function getNavSections({ manages }: { manages: boolean }): NavSection[] {
  return [
    { title: 'Transactions', href: '/transactions', icon: WalletCards },
    { title: manages ? 'Balances' : 'Balance', href: '/balances', icon: Scale },
  ]
}

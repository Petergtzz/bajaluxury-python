import {
  ArrowLeftRight,
  ClipboardCheck,
  FileText,
  House,
  type LucideIcon,
  ReceiptText,
  Scale,
  ScrollText,
  Settings,
  User,
  Users,
  WalletCards,
} from 'lucide-react'

export type NavLink = { title: string; href: string; icon: LucideIcon }

export type NavSection = NavLink & {
  /** Pages folded under the section, unfolded while one of them is showing. */
  items?: NavLink[]
  /** Where it counts as showing, when that is wider than its link: all of Settings. */
  match?: string
}

/** The sidebar, for what someone with these rights may open. */
export function getNavSections({
  manages,
  ownsCompany,
}: {
  manages: boolean
  ownsCompany: boolean
}): NavSection[] {
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
    // The houses and the people: who sees which, and who may change what.
    ...(manages
      ? [
          {
            title: 'Team',
            href: '/team/properties',
            icon: Users,
            items: [
              { title: 'Properties', href: '/team/properties', icon: House },
              { title: 'Users', href: '/team/users', icon: User },
            ],
          },
        ]
      : []),
    // Settings keep their pages in a tab row on the page itself, so the sidebar
    // carries one entry and the first tab someone has is where it lands.
    {
      title: 'Settings',
      href: getSettingsTabs({ manages, ownsCompany })[0]?.href ?? '/settings/profile',
      icon: Settings,
      match: '/settings',
    },
  ]
}

/**
 * The settings pages, and who may have one.
 *
 * Every page here changes something, so a page somebody may not change is a
 * page of forms that refuse to save. Profile is everyone's own.
 */
const SETTINGS_PAGES: { title: string; who?: 'manages' | 'ownsCompany' }[] = [
  { title: 'Company', who: 'ownsCompany' },
  { title: 'Options', who: 'manages' },
  { title: 'Charges', who: 'manages' },
  { title: 'Connections', who: 'manages' },
  { title: 'Profile' },
]

/** The settings pages this person has, in the order their tab row lists them. */
export const getSettingsTabs = (can: {
  manages: boolean
  ownsCompany: boolean
}): { title: string; href: string }[] =>
  SETTINGS_PAGES.filter((page) => !page.who || can[page.who]).map(({ title }) => ({
    title,
    href: `/settings/${title.toLowerCase()}`,
  }))

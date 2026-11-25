/**
 * A page's tabs, kept in the address bar.
 *
 * Three pages split themselves in two the same way - what is set up and what
 * has happened - and each had written out its own copy of the same four lines.
 * The first tab is where the page starts, and it is left out of the address, so
 * the bare URL is the page rather than the page plus a redundant `?tab=`.
 */
const PARAM = 'tab'

export type PageTabs<Tab extends string> = {
  tabs: readonly Tab[]
  labels: Record<Tab, string>
  /** The tab an address asks for, or the first one. */
  parse: (params: URLSearchParams) => Tab
  /** The address for a tab, leaving the default one out of it. */
  search: (tab: Tab) => string
}

export const makeTabs = <const Tab extends string>(
  tabs: readonly Tab[],
  labels: Record<Tab, string>,
): PageTabs<Tab> => ({
  tabs,
  labels,
  parse: (params) => tabs.find((tab) => tab === params.get(PARAM)) ?? tabs[0]!,
  search: (tab) => (tab === tabs[0] ? '' : `${PARAM}=${tab}`),
})

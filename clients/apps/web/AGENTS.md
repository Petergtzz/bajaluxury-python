<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# Baja Luxury web

The dashboard for the API in `../../../server`. It looks like Doorstep's (`~/Documents/projects/doorstep-python/clients/apps/web`): read it to see how a piece is done, never copy its files. The repository's root `AGENTS.md` applies too.

## Commands

Run from this directory (`pnpm install` first).

```
pnpm run dev            # http://127.0.0.1:3100, API expected on :8100 (BAJA_API_URL)
pnpm run generate       # src/lib/api/v1.ts from the API, after any API change
pnpm run lint && pnpm run typecheck && pnpm run test
pnpm run format
```

Open the app at `127.0.0.1`, where the API sets its session cookie.

## Rules

- **The browser only calls `/v1/*` on its own origin**; `next.config.ts` passes it to the API. No CORS, no tokens in the browser.
- **Call the API only through the generated client**: `unwrap(api.GET(...))` inside TanStack Query hooks in `src/hooks/`. Never write request or response types by hand; regenerate `v1.ts`.
- **Who is logged in** comes from the proxy (`src/proxy.ts`), once per page, into `SessionProvider`; `usePermissions` hides what the role can't do (the API refuses anyway).
- **Build pages from the pieces:** `AppShell` > `PageHeader` (one `PageAction`) > summary card, chips (`filter-chips.tsx`), `ListHeading` + `ListRow`, `EmptyCard`. Dialogs are `AmountField` and `FieldRows`/`FieldRow` (`dialog-fields.tsx`). A page adds no padding or width of its own.
- **Every new page goes into `getNavSections`** (`lib/navigation.ts`); the sidebar lists only pages that exist.
- **Money** comes as decimal numbers in the company's currency, and is entered in it (`useCurrency`, `AmountField`). Show it with `useMoney`, which writes it in the currency the reader chose (converted only for display), never mid-figure on two lines (`whitespace-nowrap`). **Dates** that depend on today use the company's timezone (`todayIn`); spans read as `formatRange`.
- **Filters someone might share** live in the address, parsed and written by a tested module (`lib/ledger/filters.ts`), defaults left out.
- **Query keys** start with their area (`['ledger', ...]`); a mutation refreshes its area.
- **Errors:** `setValidationErrors` for 422s on forms, `getErrorMessage` for anything shown.
- **After login or logout, load the page whole** (`window.location.assign`) so the proxy sees the cookie; return addresses go through `getSafeReturnTo`.
- **Check every screen in a real browser** in light and dark, at 375 px wide, with its dialogs open, and with no console errors.

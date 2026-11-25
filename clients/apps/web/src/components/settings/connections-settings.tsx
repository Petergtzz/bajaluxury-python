'use client'

import { Check, Copy, Plus, Smartphone, Zap } from 'lucide-react'
import { type FormEvent, type ReactNode, useState } from 'react'
import { toast } from 'sonner'

import { Panel, PlainInput } from '@/components/dialog-fields'
import { InputError } from '@/components/input-error'
import { ListRow, RowMark } from '@/components/list-row'
import { useCompany, useUser } from '@/components/session-context'
import { PageAction } from '@/components/page-header'
import { RowMenu } from '@/components/row-menu'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Spinner } from '@/components/ui/spinner'
import { useApiTokens, useCreateApiToken, useRevokeApiToken } from '@/hooks/settings'
import { getErrorMessage } from '@/lib/api/errors'
import type { ApiToken } from '@/lib/api/types'
import { tokenActivity } from '@/lib/connections'

import { SettingsPage } from './settings-layout'

/** A step of the setup: its number, what it is for, and the rows under it. */
function Step({
  number,
  title,
  description,
  children,
}: {
  number: number
  title: string
  description?: string
  children: ReactNode
}) {
  return (
    <section>
      <header className="flex items-start gap-3">
        <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-neutral-900 text-xs font-semibold text-white dark:bg-neutral-100 dark:text-neutral-900">
          {number}
        </span>
        <div className="min-w-0">
          <h3 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">
            {title}
          </h3>
          {description && (
            <p className="mt-1 text-sm text-muted-foreground">{description}</p>
          )}
        </div>
      </header>
      <div className="mt-4 border-t border-border">{children}</div>
    </section>
  )
}

/**
 * The phones that record expenses with the Shortcut, each with a token of its
 * own: a lost phone is disconnected without touching the others.
 */
export function ConnectionsSettings() {
  const [creatingKey, setCreatingKey] = useState<number | null>(null)
  const [creatingOpen, setCreatingOpen] = useState(false)
  const [created, setCreated] = useState<string | null>(null)

  return (
    <>
      <SettingsPage
        title="Connections"
        actions={
          <PageAction
            label="New connection"
            icon={<Plus className="size-4" />}
            onClick={() => {
              setCreatingKey(Date.now())
              setCreatingOpen(true)
            }}
          />
        }
      >
        {/* The token first: the Shortcut asks for it while it is being
            added, so anyone without one already is stuck at that prompt. */}
        <div className="flex flex-col gap-10">
          <TokensSection />
          <ShortcutSection />
          <BackTapSection />
        </div>
      </SettingsPage>

      {creatingKey !== null && (
        <NewConnectionDialog
          key={creatingKey}
          open={creatingOpen}
          onOpenChange={setCreatingOpen}
          onCreated={(token) => {
            setCreatingOpen(false)
            setCreated(token)
          }}
        />
      )}
      <CreatedTokenDialog token={created} onClose={() => setCreated(null)} />
    </>
  )
}

function ShortcutSection() {
  return (
    <Step
      number={2}
      title="Paste it into the Shortcut"
      description="The Baja Luxury Shortcut asks for a token when it is added, or when its token stops working."
    >
      <ul className="flex flex-col">
        <ListRow
          label="Baja Luxury, the Shortcut for iPhone and iPad"
          mark={
            <RowMark>
              <Zap className="size-5 text-muted-foreground" aria-hidden />
            </RowMark>
          }
          title="Baja Luxury"
          meta={
            <span className="min-w-0 text-pretty">
              Records an expense against a house, from the phone.
            </span>
          }
        />
      </ul>
    </Step>
  )
}

function TokensSection() {
  const user = useUser()
  const timeZone = useCompany().data?.timezone ?? 'America/Mazatlan'
  const tokens = useApiTokens()
  const items = tokens.data ?? []

  return (
    <Step
      number={1}
      title="Create your token"
      description="Add a connection with the + button, name this phone, and copy the token. It’s shown only once."
    >
      {tokens.isPending ? (
        <Spinner className="mt-4 text-muted-foreground" />
      ) : tokens.isError ? (
        <p className="py-6 text-sm text-muted-foreground">
          {getErrorMessage(tokens.error)}
        </p>
      ) : items.length === 0 ? (
        <p className="py-6 text-sm text-muted-foreground">No devices connected yet.</p>
      ) : (
        <ul className="flex flex-col">
          {items.map((token) => (
            <TokenItem
              key={token.id}
              token={token}
              owner={
                token.user.id === user.id ? null : (token.user.name ?? token.user.email)
              }
              timeZone={timeZone}
            />
          ))}
        </ul>
      )}
    </Step>
  )
}

/** Where Back Tap lives in the iPhone's Settings, one screen at a time. */
const BACK_TAP_PATH = [
  'Settings',
  'Accessibility',
  'Touch',
  'Back Tap',
  'Double Tap',
  'Baja Luxury',
]

function BackTapSection() {
  return (
    <Step number={3} title="Open it with a tap on the back">
      <p className="py-3.5 text-sm text-muted-foreground">
        {BACK_TAP_PATH.map((place, index) => (
          <span key={place}>
            {index > 0 && <span aria-hidden> › </span>}
            <span className="font-semibold whitespace-nowrap text-neutral-900 dark:text-neutral-100">
              {place}
            </span>
          </span>
        ))}
      </p>
    </Step>
  )
}

function TokenItem({
  token,
  owner,
  timeZone,
}: {
  token: ApiToken
  /** Whose token it is, when it isn't yours; the owner sees everyone's. */
  owner: string | null
  timeZone: string
}) {
  const revoke = useRevokeApiToken()

  return (
    <ListRow
      label={token.label}
      mark={
        <RowMark>
          <Smartphone className="size-5 text-muted-foreground" aria-hidden />
        </RowMark>
      }
      title={
        <span className="flex min-w-0 items-center gap-2">
          <span className="truncate">{token.label}</span>
          {owner && (
            <span className="shrink-0 text-sm font-normal text-muted-foreground">
              {owner}
            </span>
          )}
        </span>
      }
      meta={<span className="truncate">{tokenActivity(token, timeZone)}</span>}
      menu={
        <RowMenu
          label={`More for ${token.label}`}
          items={[
            {
              label: 'Revoke',
              destructive: true,
              onSelect: async () => {
                try {
                  await revoke.mutateAsync(token.id)
                } catch (error) {
                  toast.error(getErrorMessage(error))
                  return
                }
                toast.success(`${token.label} disconnected`)
              },
            },
          ]}
        />
      }
    />
  )
}

function NewConnectionDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: (token: string) => void
}) {
  const create = useCreateApiToken()
  const [name, setName] = useState('')
  const [error, setError] = useState<string>()
  const busy = create.isPending

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!name.trim()) {
      setError('Name the device, like “Ana’s iPhone”.')
      return
    }
    let created
    try {
      created = await create.mutateAsync(name.trim())
    } catch (failure) {
      setError(getErrorMessage(failure))
      return
    }
    onCreated(created.token)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader className="text-left">
          <DialogTitle className="text-base leading-4 font-medium">
            New connection
          </DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          It records as you, with what you may do. Make one for each phone.
        </p>

        <form className="grid gap-4" noValidate onSubmit={submit}>
          <Panel className="py-1">
            <PlainInput
              id="token-name"
              value={name}
              onChange={(value) => {
                setName(value)
                setError(undefined)
              }}
              placeholder="Name this device"
              disabled={busy}
              required
            />
          </Panel>

          <InputError message={error} className="text-center" />

          <Button
            type="submit"
            disabled={busy}
            className="h-12 w-full rounded-full text-base font-semibold"
          >
            {busy && <Spinner className="size-5" />}
            Create connection
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}

/** Shown once. After it closes the token exists nowhere but where it was pasted. */
function CreatedTokenDialog({
  token,
  onClose,
}: {
  token: string | null
  onClose: () => void
}) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    if (!token) return
    try {
      await navigator.clipboard.writeText(token)
    } catch {
      toast.error('Couldn’t copy. Select the token and copy it by hand.')
      return
    }
    setCopied(true)
  }

  return (
    <Dialog
      open={token !== null}
      onOpenChange={(open) => {
        if (!open) {
          setCopied(false)
          onClose()
        }
      }}
    >
      <DialogContent className="sm:max-w-md">
        <DialogHeader className="text-left">
          <DialogTitle className="text-base leading-4 font-medium">
            Copy your token now
          </DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          This is the only time it’s shown. Copy it, then paste it into the Shortcut when
          it asks.
        </p>
        <Panel className="py-3">
          <code className="block text-xs break-all select-all">{token}</code>
        </Panel>
        <Button
          type="button"
          onClick={() => void copy()}
          className="h-12 w-full rounded-full text-base font-semibold"
        >
          {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
          {copied ? 'Copied' : 'Copy token'}
        </Button>
      </DialogContent>
    </Dialog>
  )
}

'use client'

import { useRouter } from 'next/navigation'
import { Controller, useForm } from 'react-hook-form'
import { toast } from 'sonner'

import { InputError } from '@/components/input-error'
import { UserAvatar } from '@/components/account-button'
import { useCompany, useUser } from '@/components/session-context'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { useUpdateProfile } from '@/hooks/settings'
import { ClientResponseError } from '@/lib/api/client'
import { getErrorMessage, setValidationErrors } from '@/lib/api/errors'
import type { Currency } from '@/lib/api/types'
import { formatMoney } from '@/lib/format'

type Values = { name: string; currency: Currency }

const CURRENCIES: Record<Currency, string> = {
  MXN: 'Mexican pesos (MXN)',
  USD: 'US dollars (USD)',
}

export function ProfileSettings() {
  const user = useUser()
  const company = useCompany().data
  const kept = company?.currency ?? 'MXN'
  const router = useRouter()
  const updateProfile = useUpdateProfile()
  const {
    register,
    control,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting, isDirty, dirtyFields },
  } = useForm<Values>({
    values: { name: user.name ?? '', currency: user.display_currency ?? kept },
  })

  const onSubmit = handleSubmit(async (values) => {
    let saved
    try {
      saved = await updateProfile.mutateAsync({
        ...(dirtyFields.name && { name: values.name.trim() }),
        ...(dirtyFields.currency && { display_currency: values.currency }),
      })
    } catch (error) {
      if (error instanceof ClientResponseError && error.status === 422) {
        setValidationErrors(error, setError)
      } else {
        setError('root', { message: getErrorMessage(error) })
      }
      return
    }
    reset({ name: saved.name ?? '', currency: saved.display_currency ?? kept })
    toast.success('Profile saved')
    // You are read on the server: the sidebar's account button, and the
    // currency every page writes amounts in.
    router.refresh()
  })

  return (
    <form onSubmit={onSubmit} className="max-w-xl space-y-6" noValidate>
      <div className="flex items-center gap-4">
        <UserAvatar user={user} className="size-14 text-lg" />
        <div className="min-w-0">
          <div className="truncate font-medium">{user.name ?? user.email}</div>
          {user.name && (
            <div className="truncate text-sm text-muted-foreground">{user.email}</div>
          )}
        </div>
      </div>

      <div className="grid gap-2">
        <Label htmlFor="name">Name</Label>
        <Input
          id="name"
          autoComplete="name"
          placeholder="Your name"
          aria-invalid={errors.name ? true : undefined}
          {...register('name', {
            // Someone who never had a name may still change their currency.
            validate: (value) =>
              value.trim() !== '' || user.name === null || 'Enter your name.',
          })}
        />
        <p className="text-sm text-muted-foreground">
          Shown to the team instead of your email address.
        </p>
        <InputError message={errors.name?.message} />
      </div>

      <div className="grid gap-2">
        <Label htmlFor="email">Email</Label>
        <Input id="email" value={user.email} disabled readOnly />
        <p className="text-sm text-muted-foreground">
          Where your login codes are sent. It can’t be changed.
        </p>
      </div>

      <div className="grid gap-2">
        <Label htmlFor="currency">Currency</Label>
        <Controller
          control={control}
          name="currency"
          render={({ field }) => (
            <Select
              value={field.value}
              onValueChange={(value) => value && field.onChange(value)}
            >
              <SelectTrigger id="currency" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(CURRENCIES) as Currency[]).map((currency) => (
                  <SelectItem key={currency} value={currency}>
                    {CURRENCIES[currency]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
        <p className="text-sm text-muted-foreground">
          What amounts are shown in
          {company &&
            `, at ${formatMoney(Number(company.usd_exchange_rate), kept)} per US dollar`}
          . They are always entered in {kept}.
        </p>
      </div>

      <InputError message={errors.root?.message} />

      <Button type="submit" disabled={isSubmitting || !isDirty} className="h-11 px-6">
        {isSubmitting && <Spinner />}
        Save
      </Button>
    </form>
  )
}

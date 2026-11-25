'use client'

import { useMemo } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { toast } from 'sonner'

import { InputError } from '@/components/input-error'
import { useCompany } from '@/components/session-context'
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
import { useUpdateCompany } from '@/hooks/settings'
import { ClientResponseError } from '@/lib/api/client'
import { getErrorMessage, setValidationErrors } from '@/lib/api/errors'
import type { Company } from '@/lib/api/types'
import { getTimezones } from '@/lib/timezones'

type Values = { name: string; timezone: string; rate: string }

const valuesOf = (company: Company): Values => ({
  name: company.name,
  timezone: company.timezone,
  // "17.0000" is how it is stored; 17 is how it is said.
  rate: String(Number(company.usd_exchange_rate)),
})

/** The company: its name, its clock, and what a dollar is worth in its money. */
export function CompanySettings() {
  const company = useCompany()
  if (!company.data) {
    return <Spinner className="text-muted-foreground" />
  }
  return <CompanyForm company={company.data} />
}

function CompanyForm({ company }: { company: Company }) {
  const updateCompany = useUpdateCompany()
  const timezones = useMemo(() => {
    const zones = getTimezones()
    // Keep the saved zone choosable even if this browser doesn't list it.
    return zones.includes(company.timezone) ? zones : [company.timezone, ...zones]
  }, [company.timezone])
  const {
    register,
    control,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<Values>({ defaultValues: valuesOf(company) })

  const onSubmit = handleSubmit(async (values) => {
    const rate = values.rate.replace(/,/g, '').trim()
    const before = valuesOf(company)
    const body = {
      ...(values.name.trim() !== company.name && { name: values.name.trim() }),
      ...(values.timezone !== company.timezone && { timezone: values.timezone }),
      ...(rate !== before.rate && { usd_exchange_rate: rate }),
    }
    let saved
    try {
      saved = await updateCompany.mutateAsync(body)
    } catch (error) {
      if (error instanceof ClientResponseError && error.status === 422) {
        setValidationErrors(error, setError)
      } else {
        setError('root', { message: getErrorMessage(error) })
      }
      return
    }
    reset(valuesOf(saved))
    toast.success('Company saved')
  })

  return (
    <div className="max-w-xl space-y-6">
      <form onSubmit={onSubmit} className="space-y-6" noValidate>
        <div className="grid gap-2">
          <Label htmlFor="name">Name</Label>
          <Input
            id="name"
            autoComplete="organization"
            aria-invalid={errors.name ? true : undefined}
            {...register('name', {
              validate: (value) => value.trim() !== '' || 'Enter the company’s name.',
            })}
          />
          <InputError message={errors.name?.message} />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="timezone">Timezone</Label>
          <Controller
            control={control}
            name="timezone"
            render={({ field }) => (
              <Select
                value={field.value}
                onValueChange={(value) => value && field.onChange(value)}
              >
                <SelectTrigger id="timezone" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="max-h-72">
                  {timezones.map((timezone) => (
                    <SelectItem key={timezone} value={timezone}>
                      {timezone}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
          <p className="text-sm text-muted-foreground">
            Decides which day it is: when charges fall due and statements go out.
          </p>
          <InputError message={errors.timezone?.message} />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="rate">Exchange rate</Label>
          <Input
            id="rate"
            inputMode="decimal"
            aria-invalid={errors.rate ? true : undefined}
            {...register('rate', {
              validate: (value) =>
                Number(value.replace(/,/g, '')) > 0 ||
                'Enter what one US dollar is worth.',
            })}
          />
          <p className="text-sm text-muted-foreground">
            {company.currency} per US dollar, for statements in dollars and new invoices.
            Invoices already sent keep the rate they were sent at.
          </p>
          <InputError message={errors.rate?.message} />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="currency">Currency</Label>
          <Input id="currency" value={company.currency} disabled readOnly />
          <p className="text-sm text-muted-foreground">
            What every amount is kept in. It doesn’t change: everything recorded is in it.
          </p>
        </div>

        <InputError message={errors.root?.message} />

        <Button type="submit" disabled={isSubmitting || !isDirty} className="h-11 px-6">
          {isSubmitting && <Spinner />}
          Save
        </Button>
      </form>
    </div>
  )
}

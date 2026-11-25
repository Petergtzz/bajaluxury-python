'use client'

import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'

import { InputError } from '@/components/input-error'
import { UserAvatar } from '@/components/account-button'
import { useUser } from '@/components/session-context'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import { useUpdateProfile } from '@/hooks/settings'
import { ClientResponseError } from '@/lib/api/client'
import { getErrorMessage, setValidationErrors } from '@/lib/api/errors'

type Values = { name: string }

export function ProfileSettings() {
  const user = useUser()
  const router = useRouter()
  const updateProfile = useUpdateProfile()
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<Values>({ defaultValues: { name: user.name ?? '' } })

  const onSubmit = handleSubmit(async (values) => {
    let saved
    try {
      saved = await updateProfile.mutateAsync({ name: values.name.trim() })
    } catch (error) {
      if (error instanceof ClientResponseError && error.status === 422) {
        setValidationErrors(error, setError)
      } else {
        setError('root', { message: getErrorMessage(error) })
      }
      return
    }
    reset({ name: saved.name ?? '' })
    toast.success('Profile saved')
    // The sidebar's account button reads you on the server.
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
            validate: (value) => value.trim() !== '' || 'Enter your name.',
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

      <InputError message={errors.root?.message} />

      <Button type="submit" disabled={isSubmitting || !isDirty} className="h-11 px-6">
        {isSubmitting && <Spinner />}
        Save
      </Button>
    </form>
  )
}

'use client'

import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { useRequestLoginCode } from '@/hooks/auth'
import { getErrorMessage } from '@/lib/api/errors'

export function EmailForm({ returnTo, email }: { returnTo?: string; email?: string }) {
  const router = useRouter()
  const request = useRequestLoginCode()
  const form = useForm<{ email: string }>({ defaultValues: { email: email ?? '' } })

  const submit = form.handleSubmit(async ({ email }) => {
    try {
      await request.mutateAsync(email.trim())
    } catch (error) {
      form.setError('root', { message: getErrorMessage(error) })
      return
    }
    const next = new URLSearchParams({ email: email.trim() })
    if (returnTo) next.set('return_to', returnTo)
    router.push(`/login/code?${next}`)
  })

  const problem = form.formState.errors.root?.message
  return (
    <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
      <Input
        type="email"
        autoComplete="email"
        autoFocus
        required
        aria-label="Email"
        placeholder="you@example.com"
        aria-invalid={!!problem}
        {...form.register('email', { required: true })}
      />
      {problem && <p className="text-sm text-destructive">{problem}</p>}
      <Button type="submit" size="lg" disabled={form.formState.isSubmitting}>
        {form.formState.isSubmitting && <Spinner />}
        Email me a code
      </Button>
    </form>
  )
}

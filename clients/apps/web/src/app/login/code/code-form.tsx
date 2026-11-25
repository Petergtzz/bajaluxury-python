'use client'

import Link from 'next/link'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { InputOTP, InputOTPSlot } from '@/components/ui/input-otp'
import { Spinner } from '@/components/ui/spinner'
import { useAuthenticateLoginCode } from '@/hooks/auth'
import { getErrorMessage } from '@/lib/api/errors'
import { getSafeReturnTo } from '@/lib/return-to'

const LENGTH = 6

export function CodeForm({ email, returnTo }: { email: string; returnTo?: string }) {
  const authenticate = useAuthenticateLoginCode()
  const [code, setCode] = useState('')
  const [problem, setProblem] = useState<string | null>(null)

  const submit = async (value: string) => {
    setProblem(null)
    try {
      await authenticate.mutateAsync({ email, code: value })
    } catch (error) {
      setProblem(getErrorMessage(error))
      setCode('')
      return
    }
    // A full load, so the proxy sees the new session cookie.
    window.location.assign(getSafeReturnTo(returnTo))
  }

  const busy = authenticate.isPending || authenticate.isSuccess
  return (
    <form
      className="flex flex-col items-center gap-6"
      onSubmit={(event) => {
        event.preventDefault()
        if (code.length === LENGTH) void submit(code)
      }}
    >
      <InputOTP
        maxLength={LENGTH}
        value={code}
        onChange={setCode}
        onComplete={submit}
        inputMode="numeric"
        pattern="^[0-9]+$"
        autoFocus
        disabled={busy}
        aria-label="Login code"
      >
        {Array.from({ length: LENGTH }, (_, index) => (
          <InputOTPSlot key={index} index={index} />
        ))}
      </InputOTP>
      {problem && <p className="text-center text-sm text-destructive">{problem}</p>}
      <Button
        type="submit"
        size="lg"
        className="w-full"
        disabled={busy || code.length < LENGTH}
      >
        {busy && <Spinner />}
        Log in
      </Button>
      <Link
        href={`/login?${new URLSearchParams({ email, ...(returnTo && { return_to: returnTo }) })}`}
        className="text-sm font-semibold text-muted-foreground hover:text-foreground"
      >
        Use another email
      </Link>
    </form>
  )
}

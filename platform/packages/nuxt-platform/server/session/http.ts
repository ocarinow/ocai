import { createError, getCookie, getHeader, setCookie, setHeader, type H3Event } from 'h3'
import type { SessionSettings } from './config.ts'
import { ConsoleSessions, SessionFailure } from './service.ts'

export interface SessionRuntime { service: ConsoleSessions; settings: SessionSettings }
export function runtime(event: H3Event): SessionRuntime {
  setHeader(event, 'cache-control', 'no-store')
  setHeader(event, 'referrer-policy', 'no-referrer')
  const result: SessionRuntime | undefined = event.context.consoleSessions
  if (!result) throw new SessionFailure()
  return result
}
export function cookieName(settings: SessionSettings, login = false): string {
  return (settings.local ? 'ocai-' : '__Host-ocai-') + (login ? 'login' : 'session')
}
export function readSession(event: H3Event, settings: SessionSettings, login = false): string {
  return getCookie(event, cookieName(settings, login)) ?? ''
}
export function writeCookie(event: H3Event, settings: SessionSettings, value: string, login = false): void {
  setCookie(event, cookieName(settings, login), value, {
    httpOnly: true, secure: !settings.local, sameSite: 'lax', path: '/',
    maxAge: value ? (login ? 300 : 28800) : 0,
  })
}
export function requireOrigin(event: H3Event, settings: SessionSettings): void {
  if (getHeader(event, 'origin') !== settings.origin || getHeader(event, 'sec-fetch-site') === 'cross-site') throw new SessionFailure(403)
}
export async function safeSession<T>(event: H3Event, operation: () => Promise<T>): Promise<T> {
  setHeader(event, 'cache-control', 'no-store')
  setHeader(event, 'referrer-policy', 'no-referrer')
  try { return await operation() }
  catch (error) {
    const failure = error instanceof SessionFailure ? error : new SessionFailure()
    // Never attach a cause: framework diagnostics must not receive tokens/SQL/URLs.
    throw createError({ statusCode: failure.status, statusMessage: failure.message, message: failure.message })
  }
}

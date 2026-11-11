import { defineEventHandler, getHeader, sendRedirect } from 'h3'
import { runtime, safeSession, writeCookie } from '../../session/http.ts'
import { SessionFailure } from '../../session/service.ts'

export default defineEventHandler(event => safeSession(event, async () => {
  const { service, settings } = runtime(event)
  if (getHeader(event, 'sec-fetch-site') === 'cross-site') throw new SessionFailure(403)
  const result = await service.begin()
  writeCookie(event, settings, result.browser, true)
  return sendRedirect(event, result.url, 302)
}))

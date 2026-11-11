import { defineEventHandler, getRequestURL, sendRedirect } from 'h3'
import { runtime, safeSession, readSession, writeCookie } from '../../session/http.ts'

export default defineEventHandler(event => safeSession(event, async () => {
  const { service, settings } = runtime(event)
  const browser = readSession(event, settings, true)
  writeCookie(event, settings, '', true)
  try {
    const url = new URL('/auth/callback', settings.origin)
    url.search = getRequestURL(event).search
    const result = await service.callback(url, browser, readSession(event, settings))
    writeCookie(event, settings, result.session)
    return sendRedirect(event, result.destination, 303)
  } catch {
    // Strip authorization parameters even on failure; never render the callback URL.
    return sendRedirect(event, '/?signin=failed', 303)
  }
}))

import { defineEventHandler, getRequestURL, sendRedirect, setHeader } from 'h3'
import { runtime, readSession, writeCookie } from '../../session/http.ts'

export default defineEventHandler(async (event) => {
  setHeader(event, 'cache-control', 'no-store')
  setHeader(event, 'referrer-policy', 'no-referrer')
  try {
    const { service, settings } = runtime(event)
    const browser = readSession(event, settings, true)
    writeCookie(event, settings, '', true)
    const url = new URL('/auth/callback', settings.origin)
    url.search = getRequestURL(event).search
    const result = await service.callback(url, browser, readSession(event, settings))
    writeCookie(event, settings, result.session)
    return sendRedirect(event, result.destination, 303)
  } catch {
    // Strip authorization parameters even on failure; never render the callback URL.
    return sendRedirect(event, '/?signin=failed', 303)
  }
})

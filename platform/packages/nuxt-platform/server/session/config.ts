/** Explicit server-only settings. No ambient credential discovery in reusable modules. */
export interface SessionSettings {
  enabled: boolean
  local: boolean
  origin: string
  issuer: string
  clientId: string
  clientSecret: string
  databaseUrl: string
  activeKey: string
  keys: string
}

export function validateSettings(settings: SessionSettings): void {
  const fail = () => { throw new Error('Invalid console session configuration.') }
  try {
    for (const value of [settings.origin, settings.issuer]) {
      const url = new URL(value)
      if (url.username || url.password || url.search || url.hash) fail()
      if (url.protocol !== 'https:' && !(settings.local && url.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname))) fail()
    }
    if (new URL(settings.origin).origin !== settings.origin) fail()
    if (!settings.clientId || !settings.clientSecret || settings.clientSecret.length < 16) fail()
    const db = new URL(settings.databaseUrl)
    if (!['postgres:', 'postgresql:'].includes(db.protocol) || !db.hostname || !db.username || !db.password || db.pathname.length < 2 || db.search || db.hash) fail()
    if (decodeURIComponent(db.username) !== 'ocai_console') fail()
    if (settings.local && !['localhost', '127.0.0.1', '[::1]'].includes(db.hostname)) fail()
  } catch { fail() }
}

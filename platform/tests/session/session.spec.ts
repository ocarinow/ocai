import { test, expect, type Page } from '@playwright/test'
import pg from 'pg'
import { createServer } from 'node:http'
import { createApp, eventHandler, toNodeListener } from 'h3'
import { writeCookie } from '../../packages/nuxt-platform/server/session/http.ts'
import { SessionServices } from './services.ts'
import { validateSettings } from '../../packages/nuxt-platform/server/session/config.ts'
import { TokenCipher, randomId, digest } from '../../packages/nuxt-platform/server/session/crypto.ts'
import { SessionStore } from '../../packages/nuxt-platform/server/session/store.ts'
import { ConsoleSessions, SessionFailure } from '../../packages/nuxt-platform/server/session/service.ts'
import type { TokenMaterial } from '../../packages/nuxt-platform/server/session/oidc.ts'

const services = new SessionServices()
test.beforeAll(async () => { await services.start() })
test.afterAll(async () => { await services.close() })

async function login(page: Page): Promise<void> {
  await page.goto(services.settings.origin)
  await page.getByRole('link', { name: 'Sign in', exact: true }).click()
  await page.getByLabel('Username or email').fill('developer')
  await page.getByLabel('Password', { exact: true }).fill(services.password)
  await page.getByRole('button', { name: 'Sign In', exact: true }).click()
  await expect(page).toHaveURL(services.settings.origin + '/')
  await expect(page.getByRole('button', { name: 'Sign out', exact: true })).toBeVisible()
}

test('real OIDC login, two replicas, rotated tokens, CSRF and local/provider logout', async ({ page }) => {
  await login(page)
  const first = await services.admin.query<{ material: string }>('SELECT material FROM console_session.session')
  expect(first.rowCount).toBe(1)
  const cookie = (await page.context().cookies()).find(c => c.name === 'ocai-session')!
  expect(cookie.httpOnly).toBe(true)
  expect(cookie.sameSite).toBe('Lax')
  expect(cookie.value).toMatch(/^[A-Za-z0-9_-]{43}$/)
  const state = await page.evaluate(() => ({ local: { ...localStorage }, session: { ...sessionStorage }, cookies: document.cookie, html: document.documentElement.outerHTML }))
  expect(Object.keys(state.local)).toEqual([])
  expect(Object.keys(state.session).filter(key => key !== 'vue-router:scroll')).toEqual([])
  expect(state.cookies.includes(cookie.value)).toBe(false)
  // Actual secrets are never included in assertion output on failure.
  const row = await services.admin.query<{ id: string; material: string }>('SELECT id,material FROM console_session.session')
  const tokens = new TokenCipher('test-v1', services.settings.keys).open(row.rows[0]!.material, 'session:' + row.rows[0]!.id) as TokenMaterial
  for (const secret of [tokens.access, tokens.refresh, tokens.idToken, services.secret, services.encryptionKey]) {
    expect(JSON.stringify(state).includes(secret)).toBe(false)
    expect(services.logs.includes(secret)).toBe(false)
  }
  const replica = await page.request.get(services.secondOrigin + '/api/auth/session')
  expect(replica.status()).toBe(200)
  expect(await replica.json()).toMatchObject({ authenticated: true })
  expect(replica.headers()['cache-control']).toBe('no-store')
  await services.admin.query("UPDATE console_session.session SET access_until=clock_timestamp()")
  const renewed = await page.request.get(services.secondOrigin + '/api/auth/session')
  expect(renewed.status()).toBe(200)
  expect(await renewed.json()).toMatchObject({ authenticated: true })
  const after = await services.admin.query<{ material: string; version: number }>('SELECT material,version FROM console_session.session')
  expect(after.rows[0]!.version).toBe(1)
  expect(after.rows[0]!.material === first.rows[0]!.material).toBe(false)
  const csrf = (await renewed.json()).csrf as string
  for (const headers of [{ origin: 'https://untrusted.example', 'x-csrf-token': csrf }, { origin: services.settings.origin, 'x-csrf-token': randomId() }]) {
    const denied = await page.request.post(services.settings.origin + '/api/auth/logout', { headers })
    expect(denied.status()).toBe(403)
  }
  await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  await expect(page.getByRole('link', { name: 'Sign in', exact: true })).toBeVisible()
  expect((await services.admin.query('SELECT id FROM console_session.session')).rowCount).toBe(0)
  const replay = await page.request.get(services.secondOrigin + '/api/auth/session', { headers: { cookie: 'ocai-session=' + cookie.value } })
  expect(await replay.json()).toEqual({ authenticated: false, csrf: null })
  // Keycloak may retain its own login. Visit the flow without assuming a password prompt.
  await page.goto(services.settings.origin + '/auth/login')
  await expect(page).toHaveURL(services.settings.origin + '/')
  const current = await page.request.get(services.settings.origin + '/api/auth/session')
  const response = await page.request.post(services.settings.origin + '/api/auth/logout', { headers: {
    origin: services.settings.origin, 'x-csrf-token': (await current.json()).csrf, 'x-provider-logout': 'true',
  } })
  const result = await response.json()
  expect(result.signedOut).toBe(true)
  expect(new URL(result.providerLogout).origin).toBe(new URL(services.settings.issuer).origin)
  expect(result.providerLogout.includes('id_token')).toBe(false)
  expect((await services.admin.query('SELECT id FROM console_session.session')).rowCount).toBe(0)
})

test('browser-bound one-use login, callback cleanup and fixed return destination', async ({ page, browser }) => {
  await page.goto(services.settings.origin + '/auth/login?returnTo=https://untrusted.example')
  const auth = new URL(page.url())
  const state = auth.searchParams.get('state')!
  expect((await services.admin.query('SELECT id FROM console_session.login WHERE id=$1', [digest(state)])).rowCount).toBe(1)
  const other = await browser.newContext()
  const stolen = await other.request.get(services.settings.origin + '/auth/callback?state=' + state + '&code=fake', { maxRedirects: 0 })
  expect(stolen.headers().location).toBe('/?signin=failed')
  expect((await services.admin.query('SELECT id FROM console_session.login WHERE id=$1', [digest(state)])).rowCount).toBe(1)
  await other.close()
  await page.getByLabel('Username or email').fill('developer')
  await page.getByLabel('Password', { exact: true }).fill(services.password)
  await page.getByRole('button', { name: 'Sign In', exact: true }).click()
  await expect(page).toHaveURL(services.settings.origin + '/')
  expect((await services.admin.query('SELECT id FROM console_session.login WHERE id=$1', [digest(state)])).rowCount).toBe(0)
  const replay = await page.request.get(services.settings.origin + '/auth/callback?state=' + state + '&code=fake', { maxRedirects: 0 })
  expect(replay.headers().location).toBe('/?signin=failed')
  expect(replay.headers()['referrer-policy']).toBe('no-referrer')
  await services.admin.query('DELETE FROM console_session.session')
})

test('database leases serialize refresh and logout defeats a late completion', async () => {
  const store = new SessionStore(services.settings)
  await store.open()
  const cipher = new TokenCipher('test-v1', services.settings.keys)
  const material: TokenMaterial = { access: randomId(), refresh: randomId(), idToken: randomId(), subject: 'test', expiresIn: 300 }
  let release!: () => void
  let entered!: () => void
  const begun = new Promise<void>(resolve => { entered = resolve })
  const hold = new Promise<void>(resolve => { release = resolve })
  let refreshes = 0
  const identity = { authorization: async () => '', exchange: async () => material, logoutUrl: () => '',
    refresh: async () => { refreshes++; entered(); await hold; return material } }
  const service = new ConsoleSessions(store, cipher, identity)
  const session = randomId(), id = digest(session), csrf = randomId()
  try {
    await store.create(id, cipher.seal(material, 'session:' + id), csrf, 1)
    const inFlight = service.current(session).then(() => 200, (error: unknown) => error instanceof SessionFailure ? error.status : 500)
    await begun
    await expect(service.current(session)).rejects.toMatchObject({ status: 503 })
    expect(refreshes).toBe(1)
    await service.logout(session, csrf, false)
    release()
    expect(await inFlight).toBe(401)
    expect(await store.read(id)).toBeUndefined()
  } finally { release(); await store.close() }
})

test('expiry, crashed refresh, rotation, ciphertext binding and database role isolation', async () => {
  const store = new SessionStore(services.settings)
  await store.open()
  const cipher = new TokenCipher('test-v1', services.settings.keys)
  const material: TokenMaterial = { access: randomId(), refresh: randomId(), idToken: randomId(), subject: 'test', expiresIn: 300 }
  const identity = { authorization: async () => '', exchange: async () => material, logoutUrl: () => '', refresh: async () => material }
  const service = new ConsoleSessions(store, cipher, identity)
  try {
    for (const field of ['idle_until', 'absolute_until', 'lease_until']) {
      const session = randomId(), id = digest(session)
      await store.create(id, cipher.seal(material, 'session:' + id), randomId(), 300)
      await services.admin.query(`UPDATE console_session.session SET ${field}=clock_timestamp()-interval '1 second' WHERE id=$1`, [id])
      await expect(service.current(session)).rejects.toMatchObject({ status: 401 })
      expect(await store.renewed(id, 0, 'unused', 300)).toBe(false)
    }
    const state = randomId()
    await store.createLogin(digest(state), digest('browser'), cipher.seal({}, 'login:' + digest(state)))
    await services.admin.query("UPDATE console_session.login SET expires_at=clock_timestamp()-interval '1 second'")
    expect(await store.consumeLogin(digest(state), digest('browser'))).toBeUndefined()
    await store.cleanup()
    expect((await services.admin.query('SELECT id FROM console_session.session')).rowCount).toBe(0)
    expect((await services.admin.query('SELECT id FROM console_session.login')).rowCount).toBe(0)
    const old = cipher.seal(material, 'session:old')
    const rotated = new TokenCipher('test-v2', JSON.stringify({ 'test-v1': services.encryptionKey, 'test-v2': 'ab'.repeat(32) }))
    expect(rotated.open(old, 'session:old')).toEqual(material)
    expect(rotated.seal(material, 'session:new').startsWith('test-v2.')).toBe(true)
    expect(() => rotated.open(old, 'session:other')).toThrow('Console session material is unavailable.')
    expect(() => new TokenCipher('test-v2', JSON.stringify({ 'test-v2': 'ab'.repeat(32) })).open(old, 'session:old')).toThrow()
    const session = randomId(), id = digest(session)
    await store.create(id, old, randomId(), 300)
    await expect(service.current(session)).rejects.toMatchObject({ status: 401 })
    expect(await store.read(id)).toBeUndefined()
    const isolated = new pg.Pool({ connectionString: services.settings.databaseUrl })
    try {
      await expect(isolated.query('CREATE TABLE console_session.forbidden(id integer)')).rejects.toThrow()
      await expect(isolated.query('SELECT * FROM platform.organizations')).rejects.toThrow()
      const denied = await services.admin.query<{ allowed: boolean }>("SELECT has_table_privilege('ocai_gateway','console_session.session','SELECT') AS allowed")
      expect(denied.rows[0]?.allowed).toBe(false)
    } finally { await isolated.end() }
    for (const patch of [{ origin: 'http://example.com' }, { databaseUrl: 'postgresql://postgres:secret@localhost/db' }, { clientSecret: '' }]) {
      expect(() => validateSettings({ ...services.settings, ...patch, local: false })).toThrow('Invalid console session configuration.')
    }
    expect(() => new TokenCipher('missing', '{}')).toThrow('Invalid console encryption configuration.')
  } finally { await store.close() }
})


test('enabled invalid configuration exits startup and production cookies are host-only', async () => {
  expect(await services.rejectStartup({ keys: '{}' })).toBe(1)
  expect(await services.rejectStartup({ origin: 'http://untrusted.example', local: false })).toBe(1)
  const app = createApp().use(eventHandler(event => {
    writeCookie(event, { ...services.settings, local: false }, randomId())
    return 'ok'
  }))
  const server = createServer(toNodeListener(app))
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve))
  try {
    const address = server.address()
    if (!address || typeof address === 'string') throw new Error('No test address.')
    const result = await fetch('http://127.0.0.1:' + address.port)
    const cookie = result.headers.get('set-cookie')!
    expect(cookie.startsWith('__Host-ocai-session=')).toBe(true)
    for (const attribute of ['HttpOnly', 'Secure', 'SameSite=Lax', 'Path=/']) expect(cookie.includes(attribute)).toBe(true)
    expect(cookie.includes('Domain=')).toBe(false)
  } finally { await new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve())) }
})

test('tampered ciphertext and ambiguous rotated credentials require a fresh login', async () => {
  const cipher = new TokenCipher('test-v1', services.settings.keys)
  const sealed = cipher.seal({ value: 'test' }, 'record')
  const shortTag = sealed.split('.')
  shortTag[2] = Buffer.from(shortTag[2]!, 'base64url').subarray(0, 4).toString('base64url')
  expect(() => cipher.open(shortTag.join('.'), 'record')).toThrow('Console session material is unavailable.')
  const pieces = sealed.split('.')
  const bytes = Buffer.from(pieces[3]!, 'base64url')
  bytes[0] = bytes[0]! ^ 1
  pieces[3] = bytes.toString('base64url')
  expect(() => cipher.open(pieces.join('.'), 'record')).toThrow('Console session material is unavailable.')
  const store = new SessionStore(services.settings)
  const material: TokenMaterial = { access: randomId(), refresh: randomId(), idToken: randomId(), subject: 'test', expiresIn: 300 }
  let attempts = 0
  const identity = { authorization: async () => '', exchange: async () => material, logoutUrl: () => '',
    refresh: async (): Promise<TokenMaterial> => { attempts++; throw new Error('Simulated connection loss after rotation') } }
  const service = new ConsoleSessions(store, cipher, identity)
  const session = randomId(), id = digest(session)
  try {
    await store.create(id, cipher.seal(material, 'session:' + id), randomId(), 1)
    await expect(service.current(session)).rejects.toMatchObject({ status: 401 })
    await expect(service.current(session)).rejects.toMatchObject({ status: 401 })
    expect(attempts).toBe(1)
    expect(await store.read(id)).toBeUndefined()
  } finally { await store.close() }
})

test('a signed ID token with the wrong login nonce is rejected and callback URL is cleared', async ({ page }) => {
  await page.goto(services.settings.origin + '/auth/login')
  const authorization = new URL(page.url())
  authorization.searchParams.set('nonce', randomId())
  await page.goto(authorization.href)
  await page.getByLabel('Username or email').fill('developer')
  await page.getByLabel('Password', { exact: true }).fill(services.password)
  await page.getByRole('button', { name: 'Sign In', exact: true }).click()
  await expect(page).toHaveURL(services.settings.origin + '/?signin=failed')
  expect((await services.admin.query('SELECT id FROM console_session.session')).rowCount).toBe(0)
})

test('local logout succeeds during a real identity-provider outage', async ({ page }) => {
  await login(page)
  services.stopIdentity()
  await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  await expect(page.getByRole('link', { name: 'Sign in', exact: true })).toBeVisible()
  expect((await services.admin.query('SELECT id FROM console_session.session')).rowCount).toBe(0)
})

import { execFileSync, spawn, type ChildProcess } from 'node:child_process'
import { mkdtempSync, readFileSync, writeFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { resolve } from 'node:path'
import { createServer } from 'node:net'
import { randomBytes } from 'node:crypto'
import pg from 'pg'
import type { SessionSettings } from '../../packages/nuxt-platform/server/session/config.ts'

function command(program: string, args: string[], options: { env?: NodeJS.ProcessEnv; input?: string } = {}): string {
  try { return execFileSync(program, args, { ...options, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'], timeout: 120000 }).trim() }
  catch { throw new Error('Disposable session infrastructure command failed.') }
}
async function port(): Promise<number> {
  const server = createServer()
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve))
  const address = server.address()
  if (!address || typeof address === 'string') throw new Error('No test port.')
  await new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve()))
  return address.port
}
export async function ready(url: string, process?: ChildProcess): Promise<void> {
  const deadline = Date.now() + 90000
  while (Date.now() < deadline) {
    if (process && process.exitCode !== null) throw new Error('Console test instance exited before readiness.')
    try { if ((await fetch(url, { signal: AbortSignal.timeout(1000) })).ok) return } catch {}
    await new Promise(resolve => setTimeout(resolve, 250))
  }
  throw new Error('Disposable session service readiness timed out.')
}

export class SessionServices {
  readonly folder = mkdtempSync(resolve(tmpdir(), 'ocai-console-test-'))
  readonly suffix = randomBytes(8).toString('hex')
  readonly databaseName = 'ocai-console-db-' + this.suffix
  readonly identityName = 'ocai-console-idp-' + this.suffix
  readonly password = randomBytes(32).toString('hex')
  readonly secret = randomBytes(32).toString('hex')
  readonly encryptionKey = randomBytes(32).toString('hex')
  readonly processes: ChildProcess[] = []
  logs = ''
  settings!: SessionSettings
  admin!: pg.Pool
  secondOrigin = ''

  async start(): Promise<void> {
    const firstPort = await port()
    this.secondOrigin = 'http://127.0.0.1:' + await port()
    const dbPassword = randomBytes(32).toString('hex')
    const runtimePassword = randomBytes(32).toString('hex')
    const consolePassword = randomBytes(32).toString('hex')
    const env = { ...process.env, POSTGRES_PASSWORD: dbPassword, OCAI_RUNTIME_PASSWORD: runtimePassword,
      OCAI_MIGRATION_PASSWORD: randomBytes(32).toString('hex'), OCAI_CONSOLE_DATABASE_PASSWORD: consolePassword }
    command('docker', ['run', '--detach', '--name', this.databaseName, '--publish', '127.0.0.1::5432',
      '--env', 'POSTGRES_PASSWORD', '--env', 'POSTGRES_DB=ocai', readFileSync('deploy/postgres/image.txt', 'utf8').trim()], { env })
    const dbPort = command('docker', ['port', this.databaseName, '5432/tcp']).split(':').at(-1)!
    const deadline = Date.now() + 60000
    while (true) {
      try { command('docker', ['exec', this.databaseName, 'pg_isready', '-h', '127.0.0.1', '-U', 'postgres', '-d', 'ocai']); break } catch {
        if (Date.now() > deadline) throw new Error('Disposable PostgreSQL readiness timed out.')
        await new Promise(resolve => setTimeout(resolve, 250))
      }
    }
    for (const file of ['bootstrap.sql', 'console.sql', 'console.sql']) {
      command('docker', ['exec', '--interactive', '--env', 'OCAI_MIGRATION_PASSWORD', '--env', 'OCAI_RUNTIME_PASSWORD',
        '--env', 'OCAI_CONSOLE_DATABASE_PASSWORD', this.databaseName, 'psql', '-U', 'postgres', '-d', 'ocai'],
      { env, input: readFileSync('deploy/postgres/' + file, 'utf8') })
    }
    this.admin = new pg.Pool({ connectionString: `postgresql://postgres:${dbPassword}@127.0.0.1:${dbPort}/ocai`, connectionTimeoutMillis: 5000 })
    const origin = `http://127.0.0.1:${firstPort}`
    // Reuse the operator's realm recipe; credentials exist only in the private fixture.
    const realm = command('uv', ['run', '--directory', 'services/gateway', '--frozen', 'python', '-c',
      "import json, os, runpy; recipe=runpy.run_path('../../../scripts/serve_platform.py')['realm_document']; print(json.dumps(recipe(os.environ['TEST_SECRET'], os.environ['TEST_PASSWORD'], redirect_uri=os.environ['TEST_REDIRECT'])))"],
    { env: { ...process.env, TEST_SECRET: this.secret, TEST_PASSWORD: this.password, TEST_REDIRECT: origin + '/auth/callback' } })
    writeFileSync(resolve(this.folder, 'realm.json'), realm, { mode: 0o644 })
    command('docker', ['run', '--detach', '--name', this.identityName, '--publish', '127.0.0.1::8080',
      '--mount', `type=bind,source=${this.folder}/realm.json,target=/opt/keycloak/data/import/realm.json,readonly`,
      readFileSync('deploy/keycloak/image.txt', 'utf8').trim(), 'start-dev', '--import-realm'])
    const idPort = command('docker', ['port', this.identityName, '8080/tcp']).split(':').at(-1)!
    const issuer = `http://127.0.0.1:${idPort}/realms/ocai`
    await ready(issuer + '/.well-known/openid-configuration')
    this.settings = { enabled: true, local: true, origin, issuer, clientId: 'ocai-console', clientSecret: this.secret,
      databaseUrl: `postgresql://ocai_console:${consolePassword}@127.0.0.1:${dbPort}/ocai`,
      activeKey: 'test-v1', keys: JSON.stringify({ 'test-v1': this.encryptionKey }) }
    await this.console(origin)
    await this.console(this.secondOrigin)
  }

  environment(origin: string, patch: Partial<SessionSettings> = {}): NodeJS.ProcessEnv {
    const env: NodeJS.ProcessEnv = { ...process.env, HOST: '127.0.0.1', PORT: new URL(origin).port }
    for (const [key, value] of Object.entries({ ...this.settings, ...patch })) {
      const name = key.replace(/[A-Z]/g, letter => '_' + letter).toUpperCase()
      env['NUXT_SESSION_' + name] = String(value)
    }
    return env
  }
  async console(origin: string): Promise<void> {
    const child = spawn(process.execPath, ['apps/console/.output/server/index.mjs'], { env: this.environment(origin), stdio: ['ignore', 'pipe', 'pipe'] })
    this.processes.push(child)
    child.stdout?.on('data', chunk => { this.logs += String(chunk) })
    child.stderr?.on('data', chunk => { this.logs += String(chunk) })
    try { await ready(origin + '/api/auth/session', child) }
    catch { throw new Error('Console readiness failed; startup rejected: ' + this.logs.includes('Console session startup failed') + '; listening: ' + this.logs.includes('Listening')) }
  }
  async rejectStartup(patch: Partial<SessionSettings>): Promise<number | null> {
    const origin = 'http://127.0.0.1:' + await port()
    const child = spawn(process.execPath, ['apps/console/.output/server/index.mjs'], {
      env: this.environment(origin, patch), stdio: 'ignore',
    })
    this.processes.push(child)
    return await new Promise<number | null>(resolve => {
      const timer = setTimeout(() => { child.kill('SIGKILL'); resolve(null) }, 10000)
      child.once('exit', code => { clearTimeout(timer); resolve(code) })
    })
  }
  stopIdentity(): void { command('docker', ['stop', this.identityName]) }
  async close(): Promise<void> {
    for (const child of this.processes) {
      if (child.exitCode !== null) continue
      child.kill('SIGTERM')
      await new Promise<void>(resolve => {
        const timer = setTimeout(() => { child.kill('SIGKILL'); resolve() }, 5000)
        child.once('exit', () => { clearTimeout(timer); resolve() })
      })
    }
    await this.admin?.end()
    for (const name of [this.identityName, this.databaseName]) {
      try { command('docker', ['rm', '--force', '--volumes', name]) } catch {}
    }
    rmSync(this.folder, { recursive: true, force: true })
  }
}

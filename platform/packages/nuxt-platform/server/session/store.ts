import pg from 'pg'
import type { SessionSettings } from './config.ts'

export interface SessionRow {
  id: string
  material: string
  csrf: string
  version: number
  lease_until: Date | null
  access_until: Date
}

/** Short atomic statements; no database lock remains held over an OIDC request. */
export class SessionStore {
  private readonly pool: pg.Pool
  constructor(settings: SessionSettings) {
    this.pool = new pg.Pool({
      connectionString: settings.databaseUrl, ssl: settings.local ? false : { rejectUnauthorized: true },
      max: 5, connectionTimeoutMillis: 5000, idleTimeoutMillis: 10000,
      statement_timeout: 5000, query_timeout: 6000, options: '-c lock_timeout=2000',
    })
    // An idle connection error must not expose connection settings or crash the server.
    this.pool.on('error', () => {})
  }
  async open(): Promise<void> {
    const result = await this.pool.query<{ safe: boolean }>(`SELECT
      current_user = 'ocai_console' AND NOT rolsuper AND NOT rolcreaterole AND NOT rolcreatedb AND NOT rolbypassrls
      AND has_schema_privilege(current_user, 'console_session', 'USAGE')
      AND NOT has_schema_privilege(current_user, 'console_session', 'CREATE')
      AND NOT has_schema_privilege(current_user, 'platform', 'USAGE')
      AND NOT pg_has_role(current_user, 'ocai_migrator', 'MEMBER') AS safe
      FROM pg_roles WHERE rolname = current_user`)
    if (result.rows[0]?.safe !== true) throw new Error('Invalid console database privileges.')
    await this.pool.query('SELECT id, material, csrf, version, lease_until, access_until, idle_until, absolute_until FROM console_session.session LIMIT 0')
    await this.pool.query('SELECT id, browser_hash, material, expires_at FROM console_session.login LIMIT 0')
  }
  async close(): Promise<void> { await this.pool.end() }
  async createLogin(id: string, browserHash: string, material: string): Promise<void> {
    await this.pool.query('INSERT INTO console_session.login(id, browser_hash, material) VALUES ($1,$2,$3)', [id, browserHash, material])
  }
  async consumeLogin(id: string, browserHash: string): Promise<string | undefined> {
    const result = await this.pool.query<{ material: string }>('DELETE FROM console_session.login WHERE id=$1 AND browser_hash=$2 AND expires_at>clock_timestamp() RETURNING material', [id, browserHash])
    return result.rows[0]?.material
  }
  async create(id: string, material: string, csrf: string, expiresIn: number): Promise<void> {
    await this.pool.query(`INSERT INTO console_session.session(id, material, csrf, access_until)
      VALUES ($1,$2,$3,clock_timestamp()+$4*interval '1 second')`, [id, material, csrf, expiresIn])
  }
  async read(id: string): Promise<SessionRow | undefined> {
    const result = await this.pool.query<SessionRow>(`SELECT id,material,csrf,version,lease_until,access_until FROM console_session.session
      WHERE id=$1 AND idle_until>clock_timestamp() AND absolute_until>clock_timestamp()
      AND (lease_until IS NULL OR lease_until>clock_timestamp())`, [id])
    return result.rows[0]
  }
  async touch(id: string, version: number): Promise<boolean> {
    const result = await this.pool.query(`UPDATE console_session.session SET idle_until=LEAST(absolute_until,clock_timestamp()+interval '30 minutes')
      WHERE id=$1 AND version=$2 AND lease_until IS NULL AND idle_until>clock_timestamp() AND absolute_until>clock_timestamp()`, [id, version])
    return result.rowCount === 1
  }
  async lease(id: string, version: number): Promise<boolean> {
    const result = await this.pool.query(`UPDATE console_session.session SET lease_until=clock_timestamp()+interval '15 seconds',version=version+1
      WHERE id=$1 AND version=$2 AND lease_until IS NULL AND idle_until>clock_timestamp() AND absolute_until>clock_timestamp()`, [id, version])
    return result.rowCount === 1
  }
  async renewed(id: string, version: number, material: string, expiresIn: number): Promise<boolean> {
    const result = await this.pool.query(`UPDATE console_session.session SET material=$3,access_until=clock_timestamp()+$4*interval '1 second',
      lease_until=NULL,idle_until=LEAST(absolute_until,clock_timestamp()+interval '30 minutes')
      WHERE id=$1 AND version=$2 AND lease_until>clock_timestamp() AND idle_until>clock_timestamp() AND absolute_until>clock_timestamp()`, [id, version, material, expiresIn])
    return result.rowCount === 1
  }
  async revoke(id: string): Promise<void> { await this.pool.query('DELETE FROM console_session.session WHERE id=$1', [id]) }
  async cleanup(): Promise<void> {
    await this.pool.query(`DELETE FROM console_session.login WHERE id IN (SELECT id FROM console_session.login WHERE expires_at<=clock_timestamp() LIMIT 1000)`)
    await this.pool.query(`DELETE FROM console_session.session WHERE id IN (SELECT id FROM console_session.session
      WHERE idle_until<=clock_timestamp() OR absolute_until<=clock_timestamp() OR lease_until<=clock_timestamp() LIMIT 1000)`)
  }
}

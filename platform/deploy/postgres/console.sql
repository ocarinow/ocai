-- Explicit operator provisioning, additive and rerunnable; never run during app startup.
\set ON_ERROR_STOP on
\getenv console_password OCAI_CONSOLE_DATABASE_PASSWORD
BEGIN;
SELECT format('CREATE ROLE ocai_console LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS PASSWORD %L', :'console_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ocai_console') \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO ocai_console', current_database()) \gexec
CREATE SCHEMA IF NOT EXISTS console_session AUTHORIZATION ocai_migrator;
SET LOCAL ROLE ocai_migrator;
CREATE TABLE IF NOT EXISTS console_session.login (
    id text PRIMARY KEY CHECK (id ~ '^[0-9a-f]{64}$'),
    browser_hash text NOT NULL,
    material text NOT NULL,
    expires_at timestamptz NOT NULL DEFAULT clock_timestamp() + interval '5 minutes'
);
CREATE TABLE IF NOT EXISTS console_session.session (
    id text PRIMARY KEY CHECK (id ~ '^[0-9a-f]{64}$'),
    material text NOT NULL,
    csrf text NOT NULL,
    version integer NOT NULL DEFAULT 0,
    lease_until timestamptz,
    access_until timestamptz NOT NULL,
    idle_until timestamptz NOT NULL DEFAULT clock_timestamp() + interval '30 minutes',
    absolute_until timestamptz NOT NULL DEFAULT clock_timestamp() + interval '8 hours'
);
CREATE INDEX IF NOT EXISTS login_expiry ON console_session.login(expires_at);
CREATE INDEX IF NOT EXISTS session_expiry ON console_session.session(idle_until);
REVOKE ALL ON SCHEMA console_session FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA console_session FROM PUBLIC;
GRANT USAGE ON SCHEMA console_session TO ocai_console;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA console_session TO ocai_console;
COMMIT;

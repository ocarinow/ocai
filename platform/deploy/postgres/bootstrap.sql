-- Operator-only, against a dedicated application database, before migrations.
-- psql reads credentials from its process environment, not command-line arguments.
\set ON_ERROR_STOP on
\getenv migration_password OCAI_MIGRATION_PASSWORD
\getenv runtime_password OCAI_RUNTIME_PASSWORD
BEGIN;
CREATE ROLE ocai_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT
    NOBYPASSRLS PASSWORD :'migration_password';
CREATE ROLE ocai_gateway LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT
    NOBYPASSRLS PASSWORD :'runtime_password';
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', current_database()) \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO ocai_migrator, ocai_gateway',
    current_database()) \gexec
CREATE SCHEMA platform AUTHORIZATION ocai_migrator;
COMMIT;

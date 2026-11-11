-- Explicit local setup only; never rotate an existing role's credential implicitly.
\set ON_ERROR_STOP on
\getenv fga_password OCAI_FGA_DATABASE_PASSWORD
SELECT format('CREATE ROLE ocai_openfga LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE', :'fga_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ocai_openfga') \gexec
SELECT 'CREATE DATABASE openfga OWNER ocai_openfga'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'openfga') \gexec
REVOKE ALL ON DATABASE openfga FROM PUBLIC;
GRANT CONNECT ON DATABASE openfga TO ocai_openfga;

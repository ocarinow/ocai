-- Development-only identity database, isolated from platform runtime privileges.
\set ON_ERROR_STOP on
\getenv identity_password OCAI_KEYCLOAK_PASSWORD
CREATE ROLE ocai_keycloak LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT
    NOBYPASSRLS PASSWORD :'identity_password';
CREATE DATABASE keycloak OWNER ocai_keycloak;
REVOKE ALL ON DATABASE keycloak FROM PUBLIC;
GRANT CONNECT ON DATABASE keycloak TO ocai_keycloak;

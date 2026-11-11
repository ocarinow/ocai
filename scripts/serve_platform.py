"""Explicit local development orchestration; production uses qualified deployment settings."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import http.client
import json
import os
import re
import secrets
import subprocess
import tempfile
import time
import urllib.request
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local" / "platform"
SETTINGS = LOCAL / "settings.json"
PROJECT = "ocai-dev-" + hashlib.sha256(str(ROOT).encode()).hexdigest()[:10]
SECRET_NAMES = (
    "POSTGRES_PASSWORD",
    "OCAI_MIGRATION_PASSWORD",
    "OCAI_RUNTIME_PASSWORD",
    "OCAI_KEYCLOAK_PASSWORD",
    "OCAI_KEYCLOAK_ADMIN_PASSWORD",
    "OCAI_CONSOLE_SECRET",
    "OCAI_DEV_USER_PASSWORD",
)


def realm_document(secret: str, password: str, *, redirect_uri: str) -> dict[str, object]:
    """Build a development realm with no platform membership or administrative grants."""
    return {
        "realm": "ocai",
        "enabled": True,
        "sslRequired": "none",
        "registrationAllowed": False,
        "accessTokenLifespan": 300,
        "clients": [
            {
                "clientId": "ocai-console",
                "enabled": True,
                "protocol": "openid-connect",
                "publicClient": False,
                "clientAuthenticatorType": "client-secret",
                "secret": secret,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": False,
                "serviceAccountsEnabled": False,
                "implicitFlowEnabled": False,
                "redirectUris": [redirect_uri],
                "webOrigins": [],
                "attributes": {"pkce.code.challenge.method": "S256"},
                "protocolMappers": [
                    {
                        "name": "management-audience",
                        "protocol": "openid-connect",
                        "protocolMapper": "oidc-audience-mapper",
                        "config": {
                            "included.custom.audience": "ocai-management",
                            "access.token.claim": "true",
                            "id.token.claim": "false",
                        },
                    }
                ],
            }
        ],
        "users": [
            {
                "username": "developer",
                "enabled": True,
                "emailVerified": False,
                "firstName": "Local",
                "lastName": "Developer",
                "email": "developer@example.test",
                "credentials": [{"type": "password", "value": password, "temporary": False}],
            }
        ],
    }


@contextmanager
def settings_lock() -> Generator[None]:
    """Serialize local credential creation and provisioning across Task processes."""
    LOCAL.mkdir(parents=True, exist_ok=True, mode=0o700)
    LOCAL.chmod(0o700)
    descriptor = os.open(LOCAL / "settings.lock", os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(descriptor, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def save_settings(values: dict[str, str]) -> None:
    """Atomically replace the private file while its caller holds the settings lock."""
    descriptor, temporary = tempfile.mkstemp(dir=LOCAL)
    try:
        with os.fdopen(descriptor, "w") as file:
            file.write(json.dumps(values, indent=2) + "\n")
        os.replace(temporary, SETTINGS)
    finally:
        Path(temporary).unlink(missing_ok=True)


def settings() -> dict[str, str]:
    """Initialize or extend local configuration without changing existing credentials."""
    with settings_lock():
        if SETTINGS.exists():
            raw: object = json.loads(SETTINGS.read_text())
            if not isinstance(raw, dict):
                raise ValueError("Invalid local settings.")
            data = cast(dict[str, object], raw)
            if not all(isinstance(value, str) for value in data.values()):
                raise ValueError("Invalid local settings.")
            result = cast(dict[str, str], data)
        else:
            result = {name: secrets.token_hex(32) for name in SECRET_NAMES}
            result.update({"OCAI_POSTGRES_PORT": "15432", "OCAI_KEYCLOAK_PORT": "18080"})
        # Only newly introduced services gain secrets; existing identities never reset.
        for name in ("OCAI_FGA_DATABASE_PASSWORD", "OCAI_FGA_TOKEN"):
            result.setdefault(name, secrets.token_hex(32))
        result.setdefault("OCAI_FGA_PORT", "18081")
        for name in (*SECRET_NAMES, "OCAI_FGA_DATABASE_PASSWORD", "OCAI_FGA_TOKEN"):
            if not re.fullmatch(r"[0-9a-f]{64}", result.get(name, "")):
                raise ValueError("Invalid local secret; never reset existing database credentials.")
        for name in ("OCAI_POSTGRES_PORT", "OCAI_KEYCLOAK_PORT", "OCAI_FGA_PORT"):
            port = result.get(name, "")
            if not port.isascii() or not port.isdecimal() or not 1 <= int(port) <= 65535:
                raise ValueError("Invalid local port.")
        save_settings(result)
        return result


def environment(values: dict[str, str]) -> dict[str, str]:
    """Supply explicit configuration to child processes without command-line secrets."""
    env = dict(os.environ)
    env.update(values)
    for service in ("postgres", "keycloak", "openfga"):
        env[f"OCAI_{service.upper()}_IMAGE"] = (
            (ROOT / "platform" / "deploy" / service / "image.txt").read_text().strip()
        )
    env.update(
        {
            "OCAI_IDENTITY_ISSUER": f"http://localhost:{values['OCAI_KEYCLOAK_PORT']}/realms/ocai",
            "OCAI_IDENTITY_AUDIENCE": "ocai-management",
            "OCAI_CONSOLE_CLIENT_ID": "ocai-console",
            "OCAI_LOCAL_DEVELOPMENT": "1",
            "OCAI_FGA_ENDPOINT": f"http://127.0.0.1:{values['OCAI_FGA_PORT']}",
            "OCAI_FGA_STORE_ID": values.get("OCAI_FGA_STORE_ID", ""),
            "OCAI_FGA_MODEL_ID": values.get("OCAI_FGA_MODEL_ID", ""),
            "OCAI_DATABASE_URL": (
                "postgresql+psycopg://ocai_gateway:"
                + values["OCAI_RUNTIME_PASSWORD"]
                + "@127.0.0.1:"
                + values["OCAI_POSTGRES_PORT"]
                + "/ocai"
            ),
            "NUXT_GATEWAY_BASE_URL": "http://127.0.0.1:8000",
            "OCAI_MIGRATION_DATABASE_URL": (
                "postgresql+psycopg://ocai_migrator:"
                + values["OCAI_MIGRATION_PASSWORD"]
                + "@127.0.0.1:"
                + values["OCAI_POSTGRES_PORT"]
                + "/ocai"
            ),
        }
    )
    return env


def compose(
    args: list[str], env: dict[str, str], *, display: bool = False, input_text: str | None = None
) -> None:
    """Operate only this checkout's named development project."""
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--project-name",
            PROJECT,
            "--file",
            str(ROOT / "platform/deploy/compose.yml"),
            *args,
        ],
        env=env,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            "Development infrastructure command failed; check Docker and local ports."
        )
    if display:
        print(result.stdout, end="")


def wait_identity(issuer: str, *, fga: bool = False) -> None:
    """Wait for the exact local issuer, without proxies or redirect following."""

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(
            self,
            req: urllib.request.Request,
            fp: object,
            code: int,
            msg: str,
            headers: object,
            newurl: str,
        ) -> None:
            return None

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            path = "/healthz" if fga else "/.well-known/openid-configuration"
            with opener.open(issuer + path, timeout=2) as response:
                document: object = json.loads(response.read(65536))
            if isinstance(document, dict) and (
                cast(dict[str, object], document).get("status") == "SERVING"
                if fga
                else cast(dict[str, object], document).get("issuer") == issuer
            ):
                return
        except (OSError, http.client.HTTPException, ValueError):
            pass
        time.sleep(0.5)
    raise RuntimeError("Local identity provider did not become ready.")


def setup_authorization(env: dict[str, str]) -> None:
    """Explicitly prepare OpenFGA storage and one pinned model for local development."""
    compose(
        [
            "exec",
            "--no-TTY",
            "--env",
            "OCAI_FGA_DATABASE_PASSWORD",
            "postgres",
            "psql",
            "-U",
            "postgres",
            "-d",
            "ocai",
            "-v",
            "ON_ERROR_STOP=1",
        ],
        env,
        input_text=(ROOT / "platform/deploy/postgres/openfga.sql").read_text(),
    )
    compose(["run", "--rm", "openfga-migrate"], env)
    compose(["up", "--detach", "openfga"], env)
    wait_identity(env["OCAI_FGA_ENDPOINT"], fga=True)
    with settings_lock():
        # Reread under the lock: two setup commands must never replace pinned IDs.
        values = cast(dict[str, str], json.loads(SETTINGS.read_text()))
        result = subprocess.run(
            [
                "uv",
                "run",
                "--directory",
                "platform/services/gateway",
                "--frozen",
                "python",
                "-m",
                "app.authorization.provision",
            ],
            cwd=ROOT,
            env=environment(values),
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if result.returncode:
            raise RuntimeError("Authorization model provisioning failed.")
        identifiers: object = json.loads(result.stdout)
        if not isinstance(identifiers, dict):
            raise ValueError("Invalid authorization provisioning result.")
        for name in ("OCAI_FGA_STORE_ID", "OCAI_FGA_MODEL_ID"):
            value = cast(dict[str, object], identifiers).get(name)
            if not isinstance(value, str) or not re.fullmatch(r"[0-9A-HJKMNP-TV-Z]{26}", value):
                raise ValueError("Invalid authorization provisioning identifier.")
            values[name] = value
        save_settings(values)
    print("OpenFGA storage and pinned authorization model are ready.")


def main() -> int:
    """Run one explicit development operation without logging generated credentials."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation",
        choices=(
            "init",
            "postgres",
            "keycloak",
            "openfga",
            "authorization-setup",
            "authorization",
            "operator",
            "migrate",
            "gateway",
            "console",
            "status",
            "stop",
        ),
    )
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        values = settings()
        env = environment(values)
        if args.operation == "init":
            realm = LOCAL / "realm.json"
            if not realm.exists():
                realm.write_text(
                    json.dumps(
                        realm_document(
                            values["OCAI_CONSOLE_SECRET"],
                            values["OCAI_DEV_USER_PASSWORD"],
                            redirect_uri="http://localhost:3000/auth/callback",
                        )
                    )
                )
                # Private parent directory protects host access; container UID needs read access.
                realm.chmod(0o644)
            print("Local settings initialized in .local/platform (credentials are not printed).")
        elif args.operation == "postgres":
            compose(["up", "--detach", "--wait", "postgres"], env)
            print("PostgreSQL is ready on the configured loopback port.")
        elif args.operation == "keycloak":
            compose(["up", "--detach", "keycloak"], env)
            wait_identity(env["OCAI_IDENTITY_ISSUER"])
            print("Keycloak is ready at " + env["OCAI_IDENTITY_ISSUER"])
        elif args.operation == "authorization-setup":
            setup_authorization(env)
        elif args.operation == "openfga":
            compose(["up", "--detach", "openfga"], env)
            wait_identity(env["OCAI_FGA_ENDPOINT"], fga=True)
            print("OpenFGA is ready on its configured loopback port.")
        elif args.operation in {"status", "stop"}:
            compose(["ps"] if args.operation == "status" else ["stop"], env, display=True)
        else:
            commands = {
                "authorization": [
                    "uv",
                    "run",
                    "--directory",
                    "platform/services/gateway",
                    "--frozen",
                    "python",
                    "-m",
                    "app.authorization.operator",
                    "worker",
                    "--local",
                ],
                "gateway": [
                    "uv",
                    "run",
                    "--directory",
                    "platform/services/gateway",
                    "--frozen",
                    "python",
                    "-m",
                    "app.main",
                ],
                "migrate": [
                    "uv",
                    "run",
                    "--directory",
                    "platform/services/gateway",
                    "--frozen",
                    "python",
                    "-m",
                    "app.storage.migrate",
                    "--local",
                ],
                "console": ["npm", "run", "dev", "--prefix", "platform"],
            }
            if args.operation == "operator":
                commands["operator"] = [
                    "uv",
                    "run",
                    "--directory",
                    "platform/services/gateway",
                    "--frozen",
                    "python",
                    "-m",
                    "app.authorization.operator",
                    *args.arguments,
                    "--local",
                ]
            # `operation` is restricted by argparse `choices` to the keys of `commands`;
            # argv is ours, so Semgrep's tainted-subprocess rule does not apply here.
            return subprocess.run(
                commands[args.operation],  # nosemgrep
                cwd=ROOT,
                env=env,
                check=False,
            ).returncode
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        print("Local service operation failed; verify Docker, settings and available ports.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

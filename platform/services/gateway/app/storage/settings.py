"""Validated explicit connection settings with a deliberately redacted repr."""

import os
from dataclasses import dataclass
from dataclasses import field

from sqlalchemy.engine import URL
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


@dataclass(frozen=True)
class DatabaseSettings:
    dsn: str = field(repr=False)
    local: bool = False

    def __post_init__(self) -> None:
        self.url()

    @classmethod
    def from_env(cls, name: str, *, local: bool = False) -> "DatabaseSettings":
        """Read a named setting only when explicitly requested by an operator."""
        value = os.environ.get(name)
        if not value:
            raise ValueError("Database connection setting is required.")
        return cls(value, local=local)

    def url(self) -> URL:
        """Validate connection policy without exposing a rejected DSN."""
        try:
            url = make_url(self.dsn)
            valid = (
                url.drivername == "postgresql+psycopg"
                and bool(url.username and url.password and url.database and url.host)
                and set(url.query) <= {"sslmode", "sslrootcert"}
                and (url.port is None or 1 <= url.port <= 65535)
            )
        except (ArgumentError, ValueError):
            raise ValueError("Invalid database connection configuration.") from None
        if not valid:
            raise ValueError("Invalid database connection configuration.")
        if self.local:
            if url.host not in {"127.0.0.1", "localhost", "::1"}:
                raise ValueError("Local database profile requires a loopback host.")
        elif url.query.get("sslmode") != "verify-full":
            raise ValueError("Database TLS must verify the server identity.")
        return url

    def connection_options(self) -> dict[str, str | int]:
        """Bound connection, statement and lock waits, including idle transactions."""
        return {
            "connect_timeout": 5,
            "options": (
                "-c statement_timeout=5000 -c lock_timeout=2000 "
                "-c idle_in_transaction_session_timeout=10000"
            ),
        }

"""Run migrations with optional auto-recovery for inconsistent local history."""

import os

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.exceptions import InconsistentMigrationHistory


class Command(BaseCommand):
    help = (
        "Run Django migrations and auto-recover from InconsistentMigrationHistory "
        "by resetting local PostgreSQL schema when enabled."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="Nominates a database to synchronize. Defaults to the 'default' database.",
        )

    def handle(self, *args, **options) -> None:
        database = options["database"]
        try:
            call_command("migrate", database=database)
            return
        except InconsistentMigrationHistory as exc:
            if not self._auto_reset_enabled():
                raise

            connection = connections[database]
            engine = connection.settings_dict.get("ENGINE", "")
            if "postgresql" not in engine:
                raise CommandError(
                    "Automatic recovery from inconsistent migration history is enabled "
                    "but reset_db_schema supports only PostgreSQL."
                ) from exc

            self.stderr.write(
                self.style.WARNING(
                    "Detected InconsistentMigrationHistory. "
                    "Applying local PostgreSQL schema reset and retrying migrations."
                )
            )
            call_command("reset_db_schema", database=database, force=True)
            call_command("migrate", database=database)
            self.stdout.write(self.style.SUCCESS("safe_migrate recovered migration history successfully."))

    def _auto_reset_enabled(self) -> bool:
        raw = os.getenv("CORE_DB_AUTO_RESET_ON_INCONSISTENT_MIGRATIONS", "true")
        return raw.strip().lower() == "true"

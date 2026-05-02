"""Reset the PostgreSQL public schema for local MVP recovery workflows."""

from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections


class Command(BaseCommand):
    help = "Drop and recreate the PostgreSQL public schema for the selected database."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="Nominates a database to reset. Defaults to the 'default' database.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Required safety flag for destructive schema reset.",
        )

    def handle(self, *args, **options) -> None:
        database = options["database"]
        force = options["force"]
        if not force:
            raise CommandError("Schema reset is destructive. Re-run with --force to continue.")

        connection = connections[database]
        engine = connection.settings_dict.get("ENGINE", "")
        if "postgresql" not in engine:
            raise CommandError("reset_db_schema currently supports only PostgreSQL databases.")

        self.stdout.write(self.style.WARNING(f"Resetting PostgreSQL schema for database '{database}'..."))
        with connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA IF EXISTS public CASCADE;")
            cursor.execute("CREATE SCHEMA public;")
            cursor.execute("GRANT ALL ON SCHEMA public TO CURRENT_USER;")
        self.stdout.write(self.style.SUCCESS("PostgreSQL schema reset completed."))

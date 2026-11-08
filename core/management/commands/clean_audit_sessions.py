from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Purge stale audit session rows'

    def handle(self, *args, **kwargs):
        with connection.cursor() as cur:
            cur.execute("""
                DELETE FROM dbo.Audit_User_Session
                WHERE logged_at < DATEADD(HOUR, -6, SYSDATETIME());
            """)
            self.stdout.write(self.style.SUCCESS(
                f'{cur.rowcount} stale sessions removed ✅'
            ))
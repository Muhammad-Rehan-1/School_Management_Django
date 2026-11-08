"""
Rozana auto-absent command.

Use:
    python manage.py auto_absent
    python manage.py auto_absent --force          (cut-off ignore)
    python manage.py auto_absent --days 30        (30 din backfill)
    python manage.py auto_absent --loop           (khud har 5 min check)
"""

import time
from datetime import datetime
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Jin dino attendance nahi lagi un ko Absent mark kar deta hai (cut-off ke baad)'

    def add_arguments(self, parser):
        parser.add_argument('--session', type=str, default=None)
        parser.add_argument('--days', type=int, default=None, help='Backfill days')
        parser.add_argument('--force', action='store_true', help='Cut-off time ignore karo')
        parser.add_argument('--loop', action='store_true', help='Chalta rahe (har 5 min)')

    def handle(self, *args, **o):
        from core.attendance import run_auto_absent, current_session, auto_absent_status
        # ⚠️  'yourapp' ko apni app ka naam se badal dein

        def once():
            ses = o['session'] or current_session()
            st = auto_absent_status(ses)
            now = datetime.now().strftime('%d %b %Y %I:%M %p')

            self.stdout.write(f'\n⏰ {now}  |  Session: {ses}  |  Cut-off: {st["time"]}')

            if not st['enabled']:
                self.stdout.write(self.style.WARNING('⏸️  Auto-absent settings mein band hai'))
                return

            if not st['passed'] and not o['force']:
                self.stdout.write(f'⏳ Abhi {st["time"]} nahi hua — aaj ka din skip')

            res = run_auto_absent(
                session=ses,
                backfill_days=o['days'],
                verbose=True,
            )

            if res['days']:
                self.stdout.write(self.style.SUCCESS(
                    f'✅ {res["days"]} din auto-absent  |  {res["records"]} records banaye'
                ))
                for d in res['details']:
                    self.stdout.write(f'   • {d["class"]}-{d["section"]}: {d["days"]} din, {d["records"]} records')
            else:
                self.stdout.write('✓ Sab clear — koi unmarked din nahi')

        if o['loop']:
            self.stdout.write(self.style.SUCCESS('🔁 Loop mode — har 5 minute check (Ctrl+C to stop)'))
            while True:
                try:
                    once()
                except Exception as e:
                    self.stderr.write(f'⚠️  {e}')
                time.sleep(300)
        else:
            once()
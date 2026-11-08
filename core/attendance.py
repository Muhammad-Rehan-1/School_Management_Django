"""
ATTENDANCE MODULE — Views / APIs
  • Holiday Manager
  • Weekly off / Sunday — mark nahi
  • Enrolment date se pehle attendance / auto-absent nahi
  • Auto-absent 2:00 PM ke baad
"""

import json
import calendar
import threading
import traceback
from datetime import datetime, date as _date, time as _time, timedelta

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import connection, transaction
from django.db.models import Q

from .models import (
    SchoolProfile, CoreStudent,
    StudentAttendance, AttendanceLock,
    AttendanceHoliday, AttendanceSetting,
    AcademicSession,
)

STATUS_KEYS = ['P', 'A', 'L', 'T', 'H']
STATUS_LABEL = {
    'P': 'Present', 'A': 'Absent', 'L': 'Leave', 'T': 'Late', 'H': 'Half Day',
}
ACTIVE_WORDS = ('active', '1', 'yes', 'true', 'enabled', 'y', 'on')
HOLIDAY_TYPES = ('public', 'religious', 'weekend', 'exam', 'vacation', 'emergency', 'other')
AUTO_ABSENT_TIME = _time(14, 0)
AUTO_ABSENT_BACKFILL_DAYS = 150
AUTO_MARKER = 'auto-absent'
_AUTO_LOCK = threading.Lock()
_AUTO_LAST_RUN = {'key': None}


def get_school():
    return SchoolProfile.objects.filter(is_active=True).first()


def current_session():
    try:
        active = AcademicSession.objects.filter(is_current=True).first()
        if active:
            return active.session_name
        latest = AcademicSession.objects.order_by('-start_date', '-id').first()
        if latest:
            return latest.session_name
    except Exception as e:
        print('⚠️ Academic session error:', e)
    return ''


def get_sessions():
    try:
        sessions = list(
            AcademicSession.objects
            .order_by('-is_current', '-start_date', '-id')
            .values_list('session_name', flat=True)
        )
        return [str(s).strip() for s in sessions if s]
    except Exception as e:
        print('⚠️ get_sessions error:', e)
        return []


def parse_date(txt):
    try:
        return datetime.strptime(str(txt).strip(), '%Y-%m-%d').date()
    except Exception:
        return _date.today()


def parse_date_or_none(txt):
    try:
        return datetime.strptime(str(txt).strip(), '%Y-%m-%d').date()
    except Exception:
        return None


def _to_date(d):
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, _date):
        return d
    s = str(d).strip()[:10]
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except Exception:
        try:
            return datetime.strptime(s, '%m/%d/%Y').date()
        except Exception:
            return None


def photo_url(s):
    p = getattr(s, 'photo', None)
    if not p:
        return ''
    p = str(p).strip()
    if not p:
        return ''
    if p.startswith('http') or p.startswith('/'):
        return p
    return '/media/' + p


def _user(request):
    u = getattr(request, 'user', None)
    name = getattr(u, 'username', '') if u else ''
    return (name or 'system')[:100]


def student_enroll_date(s):
    """Enrolment Date — is se pehle attendance / auto-absent nahi."""
    for attr in (
        'enrolment_date', 'enrollment_date', 'enroll_date',
        'admission_date', 'date_of_admission', 'joining_date',
        'date_of_joining', 'reg_date',
    ):
        d = getattr(s, attr, None)
        d = _to_date(d)
        if d:
            return d
    return None


def student_was_enrolled_on(s, dt):
    ed = student_enroll_date(s)
    if not ed:
        return True
    return ed <= dt


def build_class_sections():
    cmap = {}
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT [class], [section], [status] FROM [Class_defination]")
            for cls, sec, status in cur.fetchall():
                c = (cls or '').strip()
                s = (sec or '').strip() or 'A'
                st = (status or '').strip().lower()
                if not c:
                    continue
                if st and st not in ACTIVE_WORDS:
                    continue
                cmap.setdefault(c, set()).add(s)
    except Exception as e:
        print('⚠️  Class_defination read error:', e)

    if not cmap:
        try:
            for r in (CoreStudent.objects.filter(is_active=True)
                      .values('student_class', 'section').distinct()):
                c = (r.get('student_class') or '').strip()
                s = (r.get('section') or 'A').strip() or 'A'
                if c:
                    cmap.setdefault(c, set()).add(s)
        except Exception as e:
            print('⚠️  Student fallback error:', e)

    return {k: sorted(v) for k, v in sorted(cmap.items())}


def _class_row(cls, sec):
    try:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT TOP 1 [room_number], [max_capacity]
                FROM [Class_defination]
                WHERE [class] = %s AND [section] = %s
            """, [cls, sec])
            return cur.fetchone()
    except Exception as e:
        print('⚠️  _class_row error:', e)
        return None


def get_room(cls, sec):
    r = _class_row(cls, sec)
    return (r[0] or '').strip() if r and r[0] else ''


def get_capacity(cls, sec):
    r = _class_row(cls, sec)
    if not r:
        return 0
    try:
        return int(str(r[1] or 0).strip() or 0)
    except Exception:
        return 0


def student_qs(cls, sec):
    cls = (cls or '').strip()
    sec = (sec or '').strip()
    if not cls:
        return CoreStudent.objects.none()
    qs = CoreStudent.objects.filter(student_class__iexact=cls, is_active=True)
    if sec:
        exact = qs.filter(section__iexact=sec)
        if exact.exists():
            return exact.order_by('roll_no', 'name')
        if sec.upper() == 'A':
            blank = qs.filter(Q(section__isnull=True) | Q(section=''))
            if blank.exists():
                return blank.order_by('roll_no', 'name')
        return CoreStudent.objects.none()
    return qs.order_by('roll_no', 'name')


def students_for_date(cls, sec, dt):
    return [s for s in student_qs(cls, sec) if student_was_enrolled_on(s, dt)]


def empty_message(cls, sec):
    try:
        all_in_class = CoreStudent.objects.filter(student_class__iexact=cls, is_active=True)
        total = all_in_class.count()
        if total == 0:
            inactive = CoreStudent.objects.filter(student_class__iexact=cls, is_active=False).count()
            msg = f'Class "{cls}" mein koi active student nahi'
            if inactive:
                msg += f' ({inactive} inactive hain)'
            return msg
        avail = sorted({
            (x or '').strip() or '(blank)'
            for x in all_in_class.values_list('section', flat=True)
        })
        return (f'Section "{sec}" khali hai. Class {cls} ke {total} student(s) '
                f'in sections mein hain: {", ".join(avail)}')
    except Exception:
        return 'Koi student nahi mila'


def get_setting(session):
    default = {
        'working_days': [1, 2, 3, 4, 5, 6],
        'min_percentage': 75,
        'allow_back_date': True,
        'back_date_days': 7,
        'late_counts_present': True,
        'auto_absent_enabled': True,
        'auto_absent_time': AUTO_ABSENT_TIME.strftime('%H:%M'),
    }
    try:
        st = AttendanceSetting.objects.filter(session=session).first()
        if not st:
            return default
        try:
            wd = json.loads(st.working_days or '[1,2,3,4,5,6]')
            if not isinstance(wd, list) or not wd:
                wd = default['working_days']
        except Exception:
            wd = default['working_days']
        cut = getattr(st, 'auto_absent_time', None)
        if isinstance(cut, _time):
            cut_str = cut.strftime('%H:%M')
        elif cut:
            cut_str = str(cut)[:5]
        else:
            cut_str = default['auto_absent_time']
        return {
            'working_days': wd,
            'min_percentage': st.min_percentage or 75,
            'allow_back_date': bool(st.allow_back_date),
            'back_date_days': st.back_date_days or 7,
            'late_counts_present': bool(st.late_counts_present),
            'auto_absent_enabled': bool(getattr(st, 'auto_absent_enabled', True)),
            'auto_absent_time': cut_str,
        }
    except Exception as e:
        print('⚠️  get_setting error:', e)
        return default


def cutoff_time(cfg):
    try:
        hh, mm = str(cfg.get('auto_absent_time') or '14:00').split(':')[:2]
        return _time(int(hh), int(mm))
    except Exception:
        return AUTO_ABSENT_TIME


def _holiday_applies(h, cls, sec):
    if getattr(h, 'applies_to_all', True):
        return True
    hc = (h.class_field or '').strip()
    hs = (h.section or '').strip()
    if hc and cls and hc.lower() != str(cls).strip().lower():
        return False
    if hs and sec and hs.lower() != str(sec).strip().lower():
        return False
    return True


def holiday_map(session, cls, sec, y, m):
    out = {}
    try:
        first = _date(y, m, 1)
        last = _date(y, m, calendar.monthrange(y, m)[1])
        qs = AttendanceHoliday.objects.filter(session=session).filter(
            Q(date__lte=last) &
            (Q(end_date__gte=first) | Q(end_date__isnull=True, date__gte=first))
        )
        for h in qs:
            if not _holiday_applies(h, cls, sec):
                continue
            d1 = h.date
            d2 = h.end_date or h.date
            cur = d1
            while cur <= d2:
                if first <= cur <= last:
                    out[cur.isoformat()] = h.title
                cur += timedelta(days=1)
    except Exception as e:
        print('⚠️  holiday_map error:', e)
    return out


def check_holiday(session, cls, dt, sec=''):
    try:
        qs = AttendanceHoliday.objects.filter(session=session).filter(
            Q(date=dt) | Q(date__lte=dt, end_date__gte=dt)
        )
        for h in qs:
            if _holiday_applies(h, cls, sec):
                return True, h.title
    except Exception as e:
        print('⚠️  check_holiday error:', e)
    return False, ''


def _holiday_set(session, d_from, d_to):
    out = {'all': {}}
    try:
        qs = AttendanceHoliday.objects.filter(session=session).filter(
            Q(date__lte=d_to) &
            (Q(end_date__gte=d_from) | Q(end_date__isnull=True, date__gte=d_from))
        )
        for h in qs:
            d1, d2 = h.date, (h.end_date or h.date)
            key = 'all' if getattr(h, 'applies_to_all', True) else (
                (h.class_field or '').strip().lower(),
                (h.section or '').strip().lower()
            )
            bucket = out.setdefault(key, {})
            cur = d1
            while cur <= d2:
                if d_from <= cur <= d_to:
                    bucket[cur] = h.title
                cur += timedelta(days=1)
    except Exception as e:
        print('⚠️  _holiday_set error:', e)
    return out


def _is_hol_fast(hset, cls, sec, d):
    if d in hset.get('all', {}):
        return True
    c, s = (cls or '').strip().lower(), (sec or '').strip().lower()
    for key, days in hset.items():
        if key == 'all':
            continue
        kc, ks = key
        if kc and kc != c:
            continue
        if ks and ks != s:
            continue
        if d in days:
            return True
    return False


def is_off_day(session, cls, sec, dt, cfg=None):
    cfg = cfg or get_setting(session)
    if dt.isoweekday() not in set(cfg['working_days']):
        return True, 'Weekly Off'
    is_hol, title = check_holiday(session, cls, dt, sec)
    if is_hol:
        return True, title
    return False, ''


def run_auto_absent(session=None, upto=None, backfill_days=None, verbose=False):
    """
    2:00 PM ke baad:
    - jis din teacher ne attendance NAHI lagayi
    - holiday / Sunday nahi
    - student enrolled hai
    → har student ki ABSENT row student_attendance mein SAVE
    """
    session = session or current_session()
    cfg = get_setting(session)
    result = {'days': 0, 'records': 0, 'details': [], 'skipped': 'none'}

    if not cfg.get('auto_absent_enabled', True):
        result['skipped'] = 'disabled'
        return result

    now = datetime.now()
    today = now.date()
    cut = cutoff_time(cfg)

    last_day = upto or today
    # Aaj tabhi jab 2:00 PM nikal chuka ho
    if last_day == today and now.time() < cut:
        last_day = today - timedelta(days=1)

    days_back = backfill_days if backfill_days is not None else AUTO_ABSENT_BACKFILL_DAYS
    first_day = last_day - timedelta(days=max(0, days_back - 1))
    if first_day > last_day:
        result['skipped'] = 'cut-off not reached'
        return result

    working = set(cfg['working_days'])
    hset = _holiday_set(session, first_day, last_day)

    # Teacher-marked din: lock hai AUR marked_by auto-absent NAHI
    teacher_days = set()
    try:
        for cls_f, sec_f, dt, by in AttendanceLock.objects.filter(
            session=session, date__gte=first_day, date__lte=last_day
        ).values_list('class_field', 'section', 'date', 'marked_by'):
            if (by or '').strip().lower() != AUTO_MARKER:
                teacher_days.add((
                    (cls_f or '').strip().lower(),
                    (sec_f or '').strip().lower(),
                    dt,
                ))
    except Exception as e:
        print('⚠️ lock load:', e)

    now_dt = datetime.now()

    for cls, secs in build_class_sections().items():
        for sec in secs:
            studs = list(student_qs(cls, sec))
            if not studs:
                continue

            ck = cls.strip().lower()
            sk = (sec or '').strip().lower()

            d = first_day
            while d <= last_day:
                # Sunday / weekly off
                if d.isoweekday() not in working:
                    d += timedelta(days=1)
                    continue
                # Holiday
                if _is_hol_fast(hset, cls, sec, d):
                    d += timedelta(days=1)
                    continue
                # Teacher ne already mark kiya (jaise 29 Sept P)
                if (ck, sk, d) in teacher_days:
                    d += timedelta(days=1)
                    continue

                enrolled = [s for s in studs if student_was_enrolled_on(s, d)]
                if not enrolled:
                    d += timedelta(days=1)
                    continue

                made = 0
                try:
                    with transaction.atomic():
                        for s in enrolled:
                            rec = StudentAttendance.objects.filter(
                                session=session, student_id=s.id, date=d
                            ).first()

                            if rec:
                                # Teacher ka P/A/L mat chhedo
                                if (rec.marked_by or '').strip().lower() != AUTO_MARKER and rec.status:
                                    continue
                                rec.status = 'A'
                                rec.marked_by = AUTO_MARKER
                                rec.remarks = 'Auto absent — attendance not marked'
                                rec.class_field = cls[:50]
                                rec.section = (sec or '')[:10]
                                rec.updated_at = now_dt
                                rec.save()
                                made += 1
                            else:
                                StudentAttendance.objects.create(
                                    session=session,
                                    student_id=s.id,
                                    date=d,
                                    class_field=cls[:50],
                                    section=(sec or '')[:10],
                                    roll_no=(getattr(s, 'roll_no', '') or '')[:30],
                                    student_name=(getattr(s, 'name', '') or '')[:150],
                                    status='A',
                                    remarks='Auto absent — attendance not marked',
                                    is_notified=False,
                                    marked_by=AUTO_MARKER,
                                    created_at=now_dt,
                                    updated_at=now_dt,
                                )
                                made += 1

                        AttendanceLock.objects.update_or_create(
                            session=session,
                            class_field=cls,
                            section=(sec or ''),
                            date=d,
                            defaults={
                                'total_students': len(enrolled),
                                'present_count': 0,
                                'absent_count': len(enrolled),
                                'leave_count': 0,
                                'late_count': 0,
                                'halfday_count': 0,
                                'is_locked': False,
                                'marked_by': AUTO_MARKER,
                                'marked_at': now_dt,
                                'updated_at': now_dt,
                            },
                        )
                except Exception as e:
                    print(f'⚠️ auto-absent {cls}-{sec} {d}:', e)
                    traceback.print_exc()
                    d += timedelta(days=1)
                    continue

                if made:
                    result['days'] += 1
                    result['records'] += made
                    if verbose:
                        print(f'   ⚡ {cls}-{sec} {d}: {made} ABSENT saved')

                d += timedelta(days=1)

    return result

def ensure_auto_absent(session=None, force=False):
    try:
        now = datetime.now()
        session = session or current_session()
        cfg = get_setting(session)
        if not cfg.get('auto_absent_enabled', True):
            return None
        if now.time() < cutoff_time(cfg) and not force:
            return None
        key = f'{session}|{now.date().isoformat()}|{now.hour}'
        if _AUTO_LAST_RUN['key'] == key and not force:
            return None
        if not _AUTO_LOCK.acquire(blocking=False):
            return None
        try:
            _AUTO_LAST_RUN['key'] = key
            res = run_auto_absent(session=session)
            if res['days']:
                print(f"⚡ Auto-absent: {res['days']} din, {res['records']} records")
            return res
        finally:
            _AUTO_LOCK.release()
    except Exception as e:
        print('⚠️  ensure_auto_absent:', e)
        return None


def auto_absent_status(session=None):
    session = session or current_session()
    cfg = get_setting(session)
    cut = cutoff_time(cfg)
    now = datetime.now()
    return {
        'enabled': bool(cfg.get('auto_absent_enabled', True)),
        'time': cut.strftime('%I:%M %p').lstrip('0'),
        'time_24': cut.strftime('%H:%M'),
        'passed': now.time() >= cut,
        'now': now.strftime('%I:%M %p').lstrip('0'),
    }


def attendance_page(request):
    active_session = current_session()
    ensure_auto_absent(active_session)
    cfg = get_setting(active_session)
    ctx = {
        'school': get_school(),
        'classes_json': json.dumps(build_class_sections()),
        'sessions_json': json.dumps(get_sessions()),
        'today': _date.today().isoformat(),
        'this_month': _date.today().strftime('%Y-%m'),
        'default_session': active_session,
        'settings_json': json.dumps(cfg),
        'auto_json': json.dumps(auto_absent_status(active_session)),
    }
    return render(request, 'attendance.html', ctx)


@require_GET
def att_data(request):
    try:
        session = request.GET.get('session') or current_session()
        cls = (request.GET.get('class') or '').strip()
        sec = (request.GET.get('section') or '').strip()
        dt = parse_date(request.GET.get('date', ''))
        if not cls:
            return JsonResponse({'success': False, 'error': 'Class required'})

        ensure_auto_absent(session)
        cfg = get_setting(session)
        students = students_for_date(cls, sec, dt)
        try:
            room = get_room(cls, sec)
            cap = get_capacity(cls, sec)
        except Exception:
            room, cap = '', 0

        is_hol, hol_title = check_holiday(session, cls, dt, sec)
        is_weekoff = dt.isoweekday() not in set(cfg['working_days'])

        if not students:
            all_cls = list(student_qs(cls, sec))
            msg = empty_message(cls, sec) if not all_cls else (
                f'Is date ({dt.isoformat()}) par koi enrolled student nahi '
                f'(enrolment date baad ki hai).'
            )
            return JsonResponse({
                'success': True, 'students': [],
                'already_marked': False, 'is_locked': False,
                'is_holiday': is_hol, 'holiday_title': hol_title,
                'is_weekoff': is_weekoff, 'room': room, 'capacity': cap,
                'auto': auto_absent_status(session), 'message': msg,
            })

        prev = {}
        try:
            for a in StudentAttendance.objects.filter(
                session=session, class_field=cls, section=sec, date=dt
            ):
                prev[a.student_id] = a
        except Exception as e:
            print('⚠️  prev attendance:', e)

        lock = None
        try:
            lock = AttendanceLock.objects.filter(
                session=session, class_field=cls, section=sec, date=dt
            ).first()
        except Exception as e:
            print('⚠️  lock:', e)

        data = []
        for i, s in enumerate(students, 1):
            a = prev.get(s.id)
            data.append({
                'sr': i, 'id': s.id,
                'roll_no': (getattr(s, 'roll_no', '') or '').strip(),
                'name': (getattr(s, 'name', '') or '').strip(),
                'father': (getattr(s, 'father_name', '') or '').strip(),
                'gender': (getattr(s, 'gender', '') or '').strip(),
                'contact': (getattr(s, 'contact', '') or '').strip(),
                'photo': photo_url(s),
                'status': a.status if a else '',
                'remarks': (a.remarks if a else '') or '',
                'auto': bool(a and (a.marked_by or '').lower() == AUTO_MARKER),
            })

        is_auto_day = bool(lock and (lock.marked_by or '').lower() == AUTO_MARKER)
        return JsonResponse({
            'success': True, 'students': data, 'room': room, 'capacity': cap,
            'already_marked': bool(lock),
            'is_locked': bool(lock and lock.is_locked),
            'is_auto': is_auto_day,
            'marked_by': lock.marked_by if lock else '',
            'marked_at': lock.marked_at.strftime('%d %b %Y, %I:%M %p') if (lock and lock.marked_at) else '',
            'is_holiday': is_hol, 'holiday_title': hol_title,
            'is_weekoff': is_weekoff, 'is_future': dt > _date.today(),
            'auto': auto_absent_status(session),
        })
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f'Server error: {e}'})


@csrf_exempt
@require_POST
def att_save(request):
    try:
        try:
            body = json.loads(request.body)
        except Exception:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'})

        session = body.get('session') or current_session()
        cls = (body.get('class') or '').strip()
        sec = (body.get('section') or '').strip()
        dt = parse_date(body.get('date', ''))
        records = body.get('records', [])
        force = bool(body.get('force'))

        if not cls:
            return JsonResponse({'success': False, 'error': 'Class required'})
        if not records:
            return JsonResponse({'success': False, 'error': 'No records received'})
        if dt > _date.today():
            return JsonResponse({'success': False, 'error': '⛔ Future date ki attendance nahi lag sakti'})

        cfg = get_setting(session)
        is_hol, hol_title = check_holiday(session, cls, dt, sec)
        if is_hol and not force:
            return JsonResponse({
                'success': False, 'is_holiday': True,
                'error': f'🎉 "{hol_title}" ki chutti hai — is din attendance count nahi hoti.'
            })
        if dt.isoweekday() not in set(cfg['working_days']) and not force:
            return JsonResponse({
                'success': False, 'is_weekoff': True,
                'error': '🛌 Weekly Off — is din attendance mark nahi ho sakti.'
            })

        lock = AttendanceLock.objects.filter(
            session=session, class_field=cls, section=sec, date=dt
        ).first()
        if lock and lock.is_locked:
            return JsonResponse({'success': False, 'error': '🔒 Ye din lock hai — edit nahi ho sakta'})

        if dt < _date.today():
            if not cfg['allow_back_date']:
                return JsonResponse({'success': False, 'error': '⛔ Back-date attendance band hai'})
            gap = (_date.today() - dt).days
            if gap > cfg['back_date_days']:
                return JsonResponse({
                    'success': False,
                    'error': f"⛔ Sirf {cfg['back_date_days']} din purani attendance edit ho sakti hai "
                             f"(ye {gap} din purani hai)"
                })

        who = _user(request)
        now = datetime.now()
        counts = {k: 0 for k in STATUS_KEYS}
        saved = deleted = skipped = 0
        valid_ids = {s.id for s in students_for_date(cls, sec, dt)}
        if not valid_ids:
            return JsonResponse({'success': False, 'error': 'Is date par koi enrolled student nahi'})

        with transaction.atomic():
            for r in records:
                try:
                    sid = int(r.get('id') or 0)
                except Exception:
                    continue
                st = (r.get('status') or '').upper().strip()
                if not sid or sid not in valid_ids:
                    skipped += 1
                    continue
                if st not in STATUS_KEYS:
                    deleted += StudentAttendance.objects.filter(
                        session=session, student_id=sid, date=dt
                    ).delete()[0]
                    continue
                StudentAttendance.objects.update_or_create(
                    session=session, student_id=sid, date=dt,
                    defaults={
                        'class_field': cls[:50], 'section': sec[:10],
                        'roll_no': (r.get('roll_no') or '')[:30],
                        'student_name': (r.get('name') or '')[:150],
                        'status': st, 'remarks': (r.get('remarks') or '')[:200],
                        'is_notified': False, 'marked_by': who,
                        'created_at': now, 'updated_at': now,
                    }
                )
                counts[st] += 1
                saved += 1

            total = len(valid_ids)
            AttendanceLock.objects.update_or_create(
                session=session, class_field=cls, section=sec, date=dt,
                defaults={
                    'total_students': total,
                    'present_count': counts['P'], 'absent_count': counts['A'],
                    'leave_count': counts['L'], 'late_count': counts['T'],
                    'halfday_count': counts['H'], 'is_locked': False,
                    'marked_by': who, 'marked_at': now, 'updated_at': now,
                }
            )

        eff = counts['P'] + counts['T'] + counts['H'] * 0.5
        pct = round(eff / total * 100, 1) if total else 0
        msg = f"✓ Saved — {saved} marked"
        if deleted:
            msg += f", {deleted} cleared"
        if skipped:
            msg += f", {skipped} skipped"
        return JsonResponse({
            'success': True, 'message': msg, 'counts': counts,
            'percentage': pct, 'marked_by': who,
            'marked_at': now.strftime('%d %b %Y, %I:%M %p'),
        })
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f'Save error: {e}'})


@csrf_exempt
@require_POST
def att_lock(request):
    try:
        try:
            b = json.loads(request.body)
        except Exception:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'})
        session = b.get('session') or current_session()
        cls = (b.get('class') or '').strip()
        sec = (b.get('section') or '').strip()
        dt = parse_date(b.get('date', ''))
        lock = AttendanceLock.objects.filter(
            session=session, class_field=cls, section=sec, date=dt
        ).first()
        if not lock:
            return JsonResponse({'success': False, 'error': 'Pehle attendance save karo'})
        lock.is_locked = bool(b.get('lock', True))
        lock.updated_at = datetime.now()
        lock.save(update_fields=['is_locked', 'updated_at'])
        return JsonResponse({
            'success': True, 'is_locked': lock.is_locked,
            'message': '🔒 Day locked' if lock.is_locked else '🔓 Day unlocked',
        })
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f'Lock error: {e}'})


@require_GET
def att_report(request):
    try:
        session = request.GET.get('session') or current_session()
        cls = (request.GET.get('class') or '').strip()
        sec = (request.GET.get('section') or '').strip()
        ym = (request.GET.get('month') or '').strip() or _date.today().strftime('%Y-%m')
        ensure_auto_absent(session)
        try:
            y, m = map(int, ym.split('-'))
            if not (1 <= m <= 12):
                raise ValueError
        except Exception:
            y, m = _date.today().year, _date.today().month
        if not cls:
            return JsonResponse({'success': False, 'error': 'Class required'})

        days_in_month = calendar.monthrange(y, m)[1]
        today = _date.today()
        cfg = get_setting(session)
        working = set(cfg['working_days'])
        hols = holiday_map(session, cls, sec, y, m)

        day_meta = []
        for d in range(1, days_in_month + 1):
            dd = _date(y, m, d)
            iso = dd.isoformat()
            is_weekly_off = dd.isoweekday() not in working
            is_hol = iso in hols
            day_meta.append({
                'd': d, 'iso': iso, 'wd': dd.strftime('%a')[:2],
                'off': is_weekly_off or is_hol,
                'holiday': hols.get(iso, 'Weekly Off' if is_weekly_off else ''),
                'is_holiday': is_hol, 'future': dd > today,
            })

        students = list(student_qs(cls, sec))
        try:
            room = get_room(cls, sec)
        except Exception:
            room = ''
        working_days_count = len([d for d in day_meta if not d['off'] and not d['future']])
        holiday_count = len([d for d in day_meta if d['is_holiday']])

        if not students:
            return JsonResponse({
                'success': True,
                'month_label': _date(y, m, 1).strftime('%B %Y'),
                'room': room, 'days': day_meta, 'rows': [],
                'holidays': [{'date': k, 'title': v} for k, v in sorted(hols.items())],
                'summary': {
                    'students': 0, 'working_days': working_days_count,
                    'marked_days': 0, 'auto_days': 0, 'holidays': holiday_count,
                    'avg_percentage': 0, 'below_min': 0,
                    'min_percentage': cfg['min_percentage'],
                },
                'message': empty_message(cls, sec),
            })

        recs = {}
        try:
            for a in StudentAttendance.objects.filter(
                session=session, class_field=cls, section=sec,
                date__year=y, date__month=m
            ).values('student_id', 'date', 'status', 'marked_by'):
                recs[(a['student_id'], a['date'].isoformat())] = (
                    a['status'], (a['marked_by'] or '').lower()
                )
        except Exception as e:
            print('⚠️  report recs:', e)

        marked_iso, auto_iso = set(), set()
        try:
            for d, by in AttendanceLock.objects.filter(
                session=session, class_field=cls, section=sec,
                date__year=y, date__month=m
            ).values_list('date', 'marked_by'):
                marked_iso.add(d.isoformat())
                if (by or '').lower() == AUTO_MARKER:
                    auto_iso.add(d.isoformat())
        except Exception as e:
            print('⚠️  report locks:', e)

        rows = []
        for s in students:
            cells = []
            c = {k: 0 for k in STATUS_KEYS}
            auto_a = 0
            work = 0
            enroll = student_enroll_date(s)

            for dm in day_meta:
                dd = _date.fromisoformat(dm['iso'])
                if dm['off']:
                    cells.append('O')
                    continue
                if dm['future']:
                    cells.append('-')
                    continue
                if enroll and dd < enroll:
                    cells.append('-')
                    continue

                rec = recs.get((s.id, dm['iso']))
                if rec:
                    st, by = rec
                    if st == 'A' and by == AUTO_MARKER:
                        cells.append('U')
                        auto_a += 1
                    else:
                        cells.append(st)
                    c[st] += 1
                    work += 1
                    continue
                if dm['iso'] in marked_iso:
                    cells.append('N')
                    c['A'] += 1
                    auto_a += 1
                    work += 1
                else:
                    cells.append('-')

            eff = c['P'] + c['T'] + c['H'] * 0.5
            pct = round(eff / work * 100, 1) if work else 0
            rows.append({
                'id': s.id,
                'roll_no': (getattr(s, 'roll_no', '') or '').strip(),
                'name': (getattr(s, 'name', '') or '').strip(),
                'father': (getattr(s, 'father_name', '') or '').strip(),
                'cells': cells,
                'P': c['P'], 'A': c['A'], 'L': c['L'], 'T': c['T'], 'H': c['H'],
                'auto_absent': auto_a, 'working': work, 'pct': pct,
            })

        tot = len(rows)
        avg = round(sum(r['pct'] for r in rows) / tot, 1) if tot else 0
        below = len([r for r in rows if r['working'] and r['pct'] < cfg['min_percentage']])
        return JsonResponse({
            'success': True,
            'month_label': _date(y, m, 1).strftime('%B %Y'),
            'room': room, 'days': day_meta, 'rows': rows,
            'holidays': [{'date': k, 'title': v} for k, v in sorted(hols.items())],
            'summary': {
                'students': tot, 'working_days': working_days_count,
                'marked_days': len(marked_iso), 'auto_days': len(auto_iso),
                'holidays': holiday_count, 'avg_percentage': avg,
                'below_min': below, 'min_percentage': cfg['min_percentage'],
            }
        })
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f'Report error: {e}'})


@require_GET
def att_holidays(request):
    try:
        session = request.GET.get('session') or current_session()
        ym = (request.GET.get('month') or '').strip()
        qs = AttendanceHoliday.objects.filter(session=session)
        if ym:
            try:
                y, m = map(int, ym.split('-'))
                first = _date(y, m, 1)
                last = _date(y, m, calendar.monthrange(y, m)[1])
                qs = qs.filter(
                    Q(date__lte=last) &
                    (Q(end_date__gte=first) | Q(end_date__isnull=True, date__gte=first))
                )
            except Exception:
                pass
        out = []
        for h in qs.order_by('date'):
            d1 = h.date
            d2 = h.end_date or h.date
            out.append({
                'id': h.pk,
                'date': d1.isoformat(),
                'end_date': h.end_date.isoformat() if h.end_date else '',
                'days': (d2 - d1).days + 1,
                'title': h.title,
                'type': h.holiday_type or 'public',
                'all': bool(h.applies_to_all),
                'class': h.class_field or '',
                'section': h.section or '',
                'past': d2 < _date.today(),
            })
        return JsonResponse({'success': True, 'holidays': out, 'types': list(HOLIDAY_TYPES)})
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_POST
def att_holiday_save(request):
    try:
        try:
            b = json.loads(request.body)
        except Exception:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'})
        session = b.get('session') or current_session()

        if b.get('delete'):
            hid = b.get('id') or b.get('holiday_id')
            if hid in ('', 'null', 'undefined', None):
                hid = None
            obj = None
            if hid not in (None, ''):
                try:
                    obj = AttendanceHoliday.objects.filter(pk=int(hid)).first()
                except (TypeError, ValueError):
                    obj = AttendanceHoliday.objects.filter(pk=hid).first()
            if obj is None:
                d1 = parse_date_or_none(b.get('date'))
                title = (b.get('title') or '').strip()
                qs = AttendanceHoliday.objects.filter(session=session)
                if d1:
                    qs = qs.filter(date=d1)
                if title:
                    qs = qs.filter(title=title)
                obj = qs.first()
            if obj is None:
                return JsonResponse({
                    'success': False,
                    'error': 'Holiday nahi mili — page refresh karke dobara try karein'
                })
            obj.delete()
            return JsonResponse({'success': True, 'message': '🗑️ Holiday removed'})

        title = (b.get('title') or '').strip()
        if not title:
            return JsonResponse({'success': False, 'error': 'Holiday ka title likhna zaroori hai'})
        d1 = parse_date_or_none(b.get('date'))
        if not d1:
            return JsonResponse({'success': False, 'error': 'Start date zaroori hai'})
        d2 = parse_date_or_none(b.get('end_date')) if b.get('end_date') else None
        if d2 and d2 < d1:
            return JsonResponse({'success': False, 'error': 'End date, start date se pehle nahi ho sakti'})
        if d2 and (d2 - d1).days > 120:
            return JsonResponse({'success': False, 'error': 'Maximum 120 din ki range allowed hai'})

        htype = (b.get('type') or 'public').strip().lower()
        if htype not in HOLIDAY_TYPES:
            htype = 'other'
        applies_all = bool(b.get('all', True))
        hcls = ('' if applies_all else (b.get('class') or '').strip())[:50]
        hsec = ('' if applies_all else (b.get('section') or '').strip())[:10]
        if not applies_all and not hcls:
            return JsonResponse({'success': False, 'error': 'Specific holiday ke liye class select karein'})

        hid = b.get('id')
        dup_qs = AttendanceHoliday.objects.filter(session=session).filter(
            Q(date__lte=(d2 or d1)) &
            (Q(end_date__gte=d1) | Q(end_date__isnull=True, date__gte=d1))
        )
        if hid:
            try:
                dup_qs = dup_qs.exclude(pk=int(hid))
            except Exception:
                pass
        for h in dup_qs:
            same_scope = (
                (getattr(h, 'applies_to_all', True) and applies_all) or
                (not applies_all and not getattr(h, 'applies_to_all', True) and
                 (h.class_field or '').strip().lower() == hcls.lower() and
                 (h.section or '').strip().lower() == hsec.lower())
            )
            if same_scope:
                return JsonResponse({
                    'success': False,
                    'error': f'⚠️ In dates par pehle se holiday mojood hai: "{h.title}" '
                             f'({h.date.strftime("%d %b")})'
                })

        defaults = {
            'session': session, 'date': d1, 'end_date': d2,
            'title': title[:120], 'holiday_type': htype[:20],
            'applies_to_all': applies_all, 'class_field': hcls, 'section': hsec,
        }
        if hid:
            try:
                AttendanceHoliday.objects.filter(pk=int(hid)).update(**defaults)
            except Exception:
                AttendanceHoliday.objects.create(created_at=datetime.now(), **defaults)
            msg = '✓ Holiday updated'
        else:
            AttendanceHoliday.objects.create(created_at=datetime.now(), **defaults)
            msg = '✓ Holiday added'

        rng_end = d2 or d1
        auto_q = StudentAttendance.objects.filter(
            session=session, date__gte=d1, date__lte=rng_end, marked_by__iexact=AUTO_MARKER
        )
        lock_q = AttendanceLock.objects.filter(
            session=session, date__gte=d1, date__lte=rng_end, marked_by__iexact=AUTO_MARKER
        )
        if not applies_all:
            auto_q = auto_q.filter(class_field__iexact=hcls)
            lock_q = lock_q.filter(class_field__iexact=hcls)
            if hsec:
                auto_q = auto_q.filter(section__iexact=hsec)
                lock_q = lock_q.filter(section__iexact=hsec)
        auto_removed = auto_q.count()
        auto_q.delete()
        lock_q.delete()
        if auto_removed:
            msg += f' — {auto_removed} auto-absent record(s) hataye gaye'

        cleared = 0
        if b.get('clear_attendance'):
            aq = StudentAttendance.objects.filter(session=session, date__gte=d1, date__lte=rng_end)
            lq = AttendanceLock.objects.filter(session=session, date__gte=d1, date__lte=rng_end)
            if not applies_all:
                aq = aq.filter(class_field__iexact=hcls)
                lq = lq.filter(class_field__iexact=hcls)
                if hsec:
                    aq = aq.filter(section__iexact=hsec)
                    lq = lq.filter(section__iexact=hsec)
            cleared = aq.count()
            aq.delete()
            lq.delete()
            if cleared:
                msg += f', {cleared} attendance record(s) clear'
        return JsonResponse({
            'success': True, 'message': msg,
            'auto_removed': auto_removed, 'cleared': cleared
        })
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f'Holiday error: {e}'})


@require_GET
def att_today_summary(request):
    try:
        session = request.GET.get('session') or current_session()
        dt = parse_date(request.GET.get('date', ''))
        cfg = get_setting(session)
        ensure_auto_absent(session)
        locks = {
            (l.class_field, l.section): l
            for l in AttendanceLock.objects.filter(session=session, date=dt)
        }
        rows = []
        tot_s = tot_p = tot_a = 0
        done = pending = auto_n = 0
        for cls, secs in build_class_sections().items():
            for sec in secs:
                n = len(students_for_date(cls, sec, dt))
                if not n:
                    continue
                off, reason = is_off_day(session, cls, sec, dt, cfg)
                if off:
                    rows.append({
                        'class': cls, 'section': sec, 'students': n,
                        'present': 0, 'absent': 0, 'leave': 0, 'late': 0,
                        'marked': False, 'locked': False, 'pct': 0,
                        'by': '', 'auto': False, 'off': True, 'off_reason': reason,
                    })
                    continue
                lk = locks.get((cls, sec))
                is_auto = bool(lk and (lk.marked_by or '').lower() == AUTO_MARKER)
                if lk:
                    done += 1
                    if is_auto:
                        auto_n += 1
                    tot_s += lk.total_students
                    tot_p += lk.present_count
                    tot_a += lk.absent_count
                    eff = lk.present_count + lk.late_count + lk.halfday_count * 0.5
                    pct = round(eff / lk.total_students * 100, 1) if lk.total_students else 0
                else:
                    pending += 1
                    tot_s += n
                    pct = 0
                rows.append({
                    'class': cls, 'section': sec,
                    'students': lk.total_students if lk else n,
                    'present': lk.present_count if lk else 0,
                    'absent': lk.absent_count if lk else 0,
                    'leave': lk.leave_count if lk else 0,
                    'late': lk.late_count if lk else 0,
                    'marked': bool(lk), 'locked': bool(lk and lk.is_locked),
                    'auto': is_auto, 'pct': pct,
                    'by': lk.marked_by if lk else '',
                    'off': False, 'off_reason': '',
                })
        return JsonResponse({
            'success': True, 'date': dt.isoformat(), 'rows': rows,
            'auto': auto_absent_status(session),
            'summary': {
                'classes_done': done, 'classes_auto': auto_n,
                'classes_pending': pending, 'total_students': tot_s,
                'total_present': tot_p, 'total_absent': tot_a,
                'overall_pct': round(tot_p / tot_s * 100, 1) if tot_s else 0,
            }
        })
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@require_GET
def att_student_history(request):
    try:
        sid = request.GET.get('student_id')
        session = request.GET.get('session') or current_session()
        if not sid:
            return JsonResponse({'success': False, 'error': 'student_id required'})
        qs = StudentAttendance.objects.filter(session=session, student_id=sid).order_by('-date')
        recs = [{
            'date': a.date.isoformat(), 'day': a.date.strftime('%a'),
            'status': a.status, 'label': STATUS_LABEL.get(a.status, a.status),
            'remarks': a.remarks or '', 'class': a.class_field, 'section': a.section,
            'auto': (a.marked_by or '').lower() == AUTO_MARKER,
        } for a in qs[:200]]
        c = {k: 0 for k in STATUS_KEYS}
        for a in qs:
            if a.status in c:
                c[a.status] += 1
        total = sum(c.values())
        eff = c['P'] + c['T'] + c['H'] * 0.5
        pct = round(eff / total * 100, 1) if total else 0
        st = CoreStudent.objects.filter(id=sid).first()
        return JsonResponse({
            'success': True,
            'student': {
                'id': sid, 'name': st.name if st else '',
                'roll_no': st.roll_no if st else '',
                'class': st.student_class if st else '',
                'section': (st.section or '') if st else '',
            },
            'records': recs, 'counts': c, 'total_days': total, 'percentage': pct,
        })
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})
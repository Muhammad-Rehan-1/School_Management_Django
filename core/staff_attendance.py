"""
STAFF ATTENDANCE
  • Holiday / Sunday — mark nahi
  • Joining date se pehle attendance / auto-absent nahi
  • 2:00 PM ke baad unmarked → ABSENT save (student_attendance jaisa)
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
from django.db import transaction
from django.db.models import Q
from django.apps import apps

from .models import (
    SchoolProfile, CoreTeacher,
    StaffAttendance, StaffAttendanceLock,
    AttendanceHoliday, AttendanceSetting,
    AcademicSession,
)

STATUS_KEYS = ['P', 'A', 'L', 'T', 'H']
STATUS_LABEL = {
    'P': 'Present', 'A': 'Absent', 'L': 'Leave',
    'T': 'Late', 'H': 'Half Day',
}
LEAVE_TYPES = {
    'sick': 'Sick Leave',
    'casual': 'Casual Leave',
    'emergency': 'Emergency',
    'official': 'Official Duty',
    'other': 'Other',
}

DEFAULT_IN = '08:00'
DEFAULT_OUT = '14:00'
DEFAULT_GRACE = 15

AUTO_ABSENT_TIME = _time(14, 0)
AUTO_ABSENT_BACKFILL_DAYS = 14
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
        print('WARNING - current academic session:', e)
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
        print('WARNING - get_sessions:', e)
        return []


def parse_date(txt):
    try:
        return datetime.strptime(str(txt).strip(), '%Y-%m-%d').date()
    except Exception:
        return _date.today()


def parse_time(txt):
    t = (txt or '').strip()
    if not t:
        return None
    for fmt in ('%H:%M', '%H:%M:%S'):
        try:
            return datetime.strptime(t, fmt).time()
        except Exception:
            continue
    return None


def t_str(t):
    return t.strftime('%H:%M') if t else ''


def _user(request):
    u = getattr(request, 'user', None)
    name = getattr(u, 'username', '') if u else ''
    return (name or 'system')[:100]


def pick(obj, *names, default=''):
    for n in names:
        v = getattr(obj, n, None)
        if v not in (None, ''):
            return v
    return default


def photo_url(p):
    if not p:
        return ''
    p = str(p).strip()
    if not p:
        return ''
    if p.startswith('http') or p.startswith('/'):
        return p
    return '/media/' + p


def _to_date(d):
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, _date):
        return d
    s = str(d).strip()[:10]
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return None


def staff_joining_date(obj):
    """Teacher / staff joining date — is se pehle absent nahi."""
    for attr in (
        'joining_date', 'join_date', 'date_of_joining',
        'appointment_date', 'date_of_appointment',
        'hire_date', 'doj', 'joined_on',
    ):
        d = _to_date(getattr(obj, attr, None))
        if d:
            return d
    return None


def staff_was_joined_on(obj, dt):
    jd = staff_joining_date(obj)
    if not jd:
        return True
    return jd <= dt


def _other_staff_model():
    for name in ('CoreStaff', 'Staff', 'CoreOtherStaff', 'OtherStaff', 'CoreEmployee', 'Employee'):
        try:
            m = apps.get_model('core', name)
            if m:
                return m
        except Exception:
            continue
    return None


def _iter_staff_objects(staff_type='all'):
    """ORM objects — joining date check ke liye."""
    if staff_type in ('all', 'teacher'):
        try:
            qs = CoreTeacher.objects.all()
            if any(f.name == 'is_active' for f in CoreTeacher._meta.get_fields()):
                qs = qs.filter(is_active=True)
            for t in qs.order_by('name'):
                yield t, 'teacher'
        except Exception as e:
            print('WARNING - teacher list:', e)

    if staff_type in ('all', 'other'):
        M = _other_staff_model()
        if M:
            try:
                qs = M.objects.all()
                if any(f.name == 'is_active' for f in M._meta.get_fields()):
                    qs = qs.filter(is_active=True)
                name_field = 'name' if any(f.name == 'name' for f in M._meta.get_fields()) else 'id'
                for s in qs.order_by(name_field):
                    yield s, 'other'
            except Exception as e:
                print('WARNING - other staff list:', e)


def _obj_to_row(obj, stype):
    return {
        'emp_id': str(pick(obj, 'emp_id', 'employee_id', 'code', 'id')),
        'name': str(pick(obj, 'name', 'full_name', 'staff_name', default='—')),
        'designation': str(pick(obj, 'designation', 'post', 'role', 'job_title',
                                 default='Teacher' if stype == 'teacher' else 'Staff')),
        'type': stype,
        'subject': str(pick(obj, 'subject', 'subjects')) if stype == 'teacher' else '',
        'phone': str(pick(obj, 'contact', 'phone', 'mobile', 'phone_number')),
        'photo': photo_url(pick(obj, 'photo', 'image', 'picture')),
        '_obj': obj,
    }


def build_staff_list(staff_type='all', desig='all', on_date=None):
    out = []
    for obj, stype in _iter_staff_objects(staff_type):
        if on_date and not staff_was_joined_on(obj, on_date):
            continue
        out.append(_obj_to_row(obj, stype))

    if desig and desig != 'all':
        out = [x for x in out if x['designation'] == desig]

    seen, clean = set(), []
    for x in out:
        if not x['emp_id'] or x['emp_id'] in seen:
            continue
        seen.add(x['emp_id'])
        x.pop('_obj', None)
        clean.append(x)
    return clean


def all_designations():
    d = {x['designation'] for x in build_staff_list('all') if x['designation']}
    return sorted(d)


def get_setting(session):
    default = {
        'working_days': [1, 2, 3, 4, 5, 6],
        'min_percentage': 75,
        'allow_back_date': True,
        'back_date_days': 7,
        'school_in': DEFAULT_IN,
        'school_out': DEFAULT_OUT,
        'grace': DEFAULT_GRACE,
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

        s_in = st.school_start_time.strftime('%H:%M') if getattr(st, 'school_start_time', None) else DEFAULT_IN
        late = st.late_after.strftime('%H:%M') if getattr(st, 'late_after', None) else None
        grace = DEFAULT_GRACE
        if late and s_in:
            try:
                h1, m1 = map(int, s_in.split(':'))
                h2, m2 = map(int, late.split(':'))
                grace = max((h2 * 60 + m2) - (h1 * 60 + m1), 0)
            except Exception:
                pass

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
            'school_in': s_in,
            'school_out': DEFAULT_OUT,
            'grace': grace,
            'auto_absent_enabled': bool(getattr(st, 'auto_absent_enabled', True)),
            'auto_absent_time': cut_str,
        }
    except Exception as e:
        print('WARNING - get_setting:', e)
        return default


def cutoff_time(cfg):
    try:
        hh, mm = str(cfg.get('auto_absent_time') or '14:00').split(':')[:2]
        return _time(int(hh), int(mm))
    except Exception:
        return AUTO_ABSENT_TIME


def holiday_map(session, y, m):
    out = {}
    try:
        first = _date(y, m, 1)
        last = _date(y, m, calendar.monthrange(y, m)[1])
        qs = AttendanceHoliday.objects.filter(session=session).filter(
            Q(date__lte=last) &
            (Q(end_date__gte=first) | Q(end_date__isnull=True, date__gte=first))
        )
        for h in qs:
            if not getattr(h, 'applies_to_all', True):
                continue
            d1, d2 = h.date, (h.end_date or h.date)
            cur = d1
            while cur <= d2:
                if first <= cur <= last:
                    out[cur.isoformat()] = h.title
                cur += timedelta(days=1)
    except Exception as e:
        print('WARNING - holiday_map:', e)
    return out


def check_holiday(session, dt):
    try:
        h = AttendanceHoliday.objects.filter(session=session).filter(
            Q(applies_to_all=True) | Q(applies_to_all__isnull=True)
        ).filter(
            Q(date=dt) | Q(date__lte=dt, end_date__gte=dt)
        ).first()
        if h:
            return True, h.title
    except Exception as e:
        print('WARNING - check_holiday:', e)
    return False, ''


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


def run_staff_auto_absent(session=None, upto=None, backfill_days=None, verbose=False):
    """
    2:00 PM baad: unmarked working day → har joined staff ki A row SAVE.
    Teacher-marked din (TEC-1 / system) skip.
    """
    session = session or current_session()
    cfg = get_setting(session)
    result = {'days': 0, 'records': 0, 'skipped': 'none'}

    if not cfg.get('auto_absent_enabled', True):
        result['skipped'] = 'disabled'
        return result

    now = datetime.now()
    today = now.date()
    cut = cutoff_time(cfg)
    last_day = upto or today
    if last_day == today and now.time() < cut:
        last_day = today - timedelta(days=1)

    days_back = backfill_days if backfill_days is not None else AUTO_ABSENT_BACKFILL_DAYS
    first_day = last_day - timedelta(days=max(0, days_back - 1))
    if first_day > last_day:
        result['skipped'] = 'cut-off not reached'
        return result

    working = set(cfg['working_days'])

    teacher_days = set()
    try:
        for dt, by in StaffAttendanceLock.objects.filter(
            session=session, date__gte=first_day, date__lte=last_day
        ).values_list('date', 'marked_by'):
            if (by or '').strip().lower() not in ('', AUTO_MARKER):
                teacher_days.add(dt)
    except Exception as e:
        print('WARNING - staff lock load:', e)

    staff_objs = list(_iter_staff_objects('all'))
    now_dt = datetime.now()

    d = first_day
    while d <= last_day:
        if d.isoweekday() not in working:
            d += timedelta(days=1)
            continue
        hol, _ = check_holiday(session, d)
        if hol:
            d += timedelta(days=1)
            continue
        if d in teacher_days:
            d += timedelta(days=1)
            continue

        joined = [(obj, stype) for obj, stype in staff_objs if staff_was_joined_on(obj, d)]
        if not joined:
            d += timedelta(days=1)
            continue

        made = 0
        try:
            with transaction.atomic():
                for obj, stype in joined:
                    emp = str(pick(obj, 'emp_id', 'employee_id', 'code', 'id'))
                    if not emp:
                        continue
                    rec = StaffAttendance.objects.filter(
                        session=session, emp_id=emp, date=d
                    ).first()
                    if rec:
                        if (rec.marked_by or '').strip().lower() != AUTO_MARKER and rec.status:
                            continue
                        rec.status = 'A'
                        rec.marked_by = AUTO_MARKER
                        rec.remarks = 'Auto absent — attendance not marked'
                        rec.check_in = None
                        rec.check_out = None
                        rec.updated_at = now_dt
                        rec.save()
                        made += 1
                    else:
                        StaffAttendance.objects.create(
                            session=session,
                            emp_id=emp[:50],
                            date=d,
                            staff_name=str(pick(obj, 'name', 'full_name', 'staff_name'))[:150],
                            designation=str(pick(obj, 'designation', 'post', 'role'))[:80],
                            staff_type=stype[:20],
                            status='A',
                            check_in=None,
                            check_out=None,
                            leave_type='',
                            remarks='Auto absent — attendance not marked',
                            marked_by=AUTO_MARKER,
                            created_at=now_dt,
                            updated_at=now_dt,
                        )
                        made += 1

                StaffAttendanceLock.objects.update_or_create(
                    session=session, date=d, staff_type='all',
                    defaults={
                        'total_staff': len(joined),
                        'present_count': 0,
                        'absent_count': len(joined),
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
            print(f'WARNING - staff auto-absent {d}:', e)
            traceback.print_exc()
            d += timedelta(days=1)
            continue

        if made:
            result['days'] += 1
            result['records'] += made
            if verbose:
                print(f'   ⚡ staff {d}: {made} ABSENT saved')
        d += timedelta(days=1)

    return result


def ensure_staff_auto_absent(session=None, force=False):
    try:
        now = datetime.now()
        session = session or current_session()
        cfg = get_setting(session)
        if not cfg.get('auto_absent_enabled', True):
            return None
        if now.time() < cutoff_time(cfg) and not force:
            return None
        key = f'staff|{session}|{now.date().isoformat()}|{now.hour}'
        if _AUTO_LAST_RUN['key'] == key and not force:
            return None
        if not _AUTO_LOCK.acquire(blocking=False):
            return None
        try:
            _AUTO_LAST_RUN['key'] = key
            res = run_staff_auto_absent(session=session)
            if res.get('days'):
                print(f"⚡ Staff auto-absent: {res['days']} din, {res['records']} records")
            return res
        finally:
            _AUTO_LOCK.release()
    except Exception as e:
        print('WARNING - ensure_staff_auto_absent:', e)
        return None


def staff_attendance_page(request):
    active_session = current_session()
    ensure_staff_auto_absent(active_session)
    cfg = get_setting(active_session)
    ctx = {
        'school': get_school(),
        'designations_json': json.dumps(all_designations()),
        'sessions_json': json.dumps(get_sessions()),
        'leave_types_json': json.dumps(LEAVE_TYPES),
        'today': _date.today().isoformat(),
        'this_month': _date.today().strftime('%Y-%m'),
        'default_session': active_session,
        'school_in': cfg['school_in'],
        'school_out': cfg['school_out'],
        'grace': cfg['grace'],
        'auto_json': json.dumps(auto_absent_status(active_session)),
    }
    return render(request, 'staff_attendance.html', ctx)


@require_GET
def sa_data(request):
    try:
        session = request.GET.get('session') or current_session()
        stype = (request.GET.get('type') or 'all').strip()
        desig = (request.GET.get('desig') or 'all').strip()
        dt = parse_date(request.GET.get('date', ''))

        ensure_staff_auto_absent(session)
        cfg = get_setting(session)
        staff = build_staff_list(stype, desig, on_date=dt)
        is_hol, hol_title = check_holiday(session, dt)
        is_weekoff = dt.isoweekday() not in set(cfg['working_days'])

        if not staff:
            return JsonResponse({
                'success': True, 'staff': [], 'already_marked': False,
                'is_locked': False, 'is_holiday': is_hol, 'holiday_title': hol_title,
                'is_weekoff': is_weekoff,
                'school_in': cfg['school_in'], 'school_out': cfg['school_out'],
                'grace': cfg['grace'],
                'auto': auto_absent_status(session),
                'message': 'Is date par koi joined staff nahi (joining date baad ki ho sakti hai).',
            })

        prev = {}
        try:
            for a in StaffAttendance.objects.filter(session=session, date=dt):
                prev[str(a.emp_id)] = a
        except Exception as e:
            print('WARNING - prev staff attendance:', e)

        lock = None
        try:
            lock = StaffAttendanceLock.objects.filter(
                session=session, date=dt, staff_type=stype
            ).first()
            if not lock:
                lock = StaffAttendanceLock.objects.filter(
                    session=session, date=dt, staff_type='all'
                ).first()
        except Exception as e:
            print('WARNING - staff lock:', e)

        data = []
        for i, s in enumerate(staff, 1):
            a = prev.get(s['emp_id'])
            data.append({
                'sr': i,
                'emp_id': s['emp_id'],
                'name': s['name'],
                'designation': s['designation'],
                'type': s['type'],
                'subject': s['subject'],
                'phone': s['phone'],
                'photo': s['photo'],
                'status': a.status if a else '',
                'check_in': t_str(a.check_in) if a else '',
                'check_out': t_str(a.check_out) if a else '',
                'leave_type': (a.leave_type if a else '') or '',
                'remarks': (a.remarks if a else '') or '',
                'auto': bool(a and (a.marked_by or '').lower() == AUTO_MARKER),
            })

        is_auto = bool(lock and (lock.marked_by or '').lower() == AUTO_MARKER)
        return JsonResponse({
            'success': True,
            'staff': data,
            'school_in': cfg['school_in'],
            'school_out': cfg['school_out'],
            'grace': cfg['grace'],
            'already_marked': bool(lock),
            'is_locked': bool(lock and lock.is_locked),
            'is_auto': is_auto,
            'marked_by': lock.marked_by if lock else '',
            'marked_at': lock.marked_at.strftime('%d %b %Y, %I:%M %p') if (lock and lock.marked_at) else '',
            'is_holiday': is_hol,
            'holiday_title': hol_title,
            'is_weekoff': is_weekoff,
            'is_future': dt > _date.today(),
            'auto': auto_absent_status(session),
        })
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f'Server error: {e}'})


@csrf_exempt
@require_POST
def sa_save(request):
    try:
        try:
            body = json.loads(request.body)
        except Exception:
            return JsonResponse({'success': False, 'error': 'Invalid JSON payload'})

        session = body.get('session') or current_session()
        stype = (body.get('type') or 'all').strip()
        dt = parse_date(body.get('date', ''))
        records = body.get('records', [])
        force = bool(body.get('force'))

        if not records:
            return JsonResponse({'success': False, 'error': 'No records received'})
        if dt > _date.today():
            return JsonResponse({'success': False, 'error': '⛔ Future date ki attendance nahi lag sakti'})

        cfg = get_setting(session)
        is_hol, hol_title = check_holiday(session, dt)
        if is_hol and not force:
            return JsonResponse({
                'success': False, 'is_holiday': True,
                'error': f'🎉 "{hol_title}" — is din attendance mark nahi ho sakti.'
            })
        if dt.isoweekday() not in set(cfg['working_days']) and not force:
            return JsonResponse({
                'success': False, 'is_weekoff': True,
                'error': '🛌 Weekly Off — is din attendance mark nahi ho sakti.'
            })

        lock = StaffAttendanceLock.objects.filter(
            session=session, date=dt, staff_type=stype
        ).first()
        if lock and lock.is_locked:
            return JsonResponse({'success': False, 'error': '🔒 This day is locked'})

        if dt < _date.today():
            if not cfg['allow_back_date']:
                return JsonResponse({'success': False, 'error': '⛔ Back-dated attendance is disabled'})
            gap = (_date.today() - dt).days
            if gap > cfg['back_date_days']:
                return JsonResponse({
                    'success': False,
                    'error': f"⛔ Sirf {cfg['back_date_days']} din purani attendance edit ho sakti hai"
                })

        who = _user(request)
        now = datetime.now()
        valid_ids = {s['emp_id'] for s in build_staff_list(stype, 'all', on_date=dt)}
        if not valid_ids:
            return JsonResponse({'success': False, 'error': 'Is date par koi joined staff nahi'})

        counts = {k: 0 for k in STATUS_KEYS}
        saved = deleted = skipped = 0

        with transaction.atomic():
            for r in records:
                emp = str(r.get('emp_id') or '').strip()
                st = (r.get('status') or '').upper().strip()
                if not emp or emp not in valid_ids:
                    skipped += 1
                    continue
                if st not in STATUS_KEYS:
                    deleted += StaffAttendance.objects.filter(
                        session=session, emp_id=emp, date=dt
                    ).delete()[0]
                    continue
                lv = (r.get('leave_type') or '').strip()
                if st != 'L':
                    lv = ''
                if lv and lv not in LEAVE_TYPES:
                    lv = 'other'
                cin = parse_time(r.get('check_in'))
                cout = parse_time(r.get('check_out'))
                if st in ('A', 'L'):
                    cin = cout = None

                StaffAttendance.objects.update_or_create(
                    session=session, emp_id=emp, date=dt,
                    defaults={
                        'staff_name': (r.get('name') or '')[:150],
                        'designation': (r.get('designation') or '')[:80],
                        'staff_type': (r.get('type') or 'teacher')[:20],
                        'status': st,
                        'check_in': cin,
                        'check_out': cout,
                        'leave_type': lv[:20],
                        'remarks': (r.get('remarks') or '')[:200],
                        'marked_by': who,
                        'created_at': now,
                        'updated_at': now,
                    }
                )
                counts[st] += 1
                saved += 1

            total = len(valid_ids)
            StaffAttendanceLock.objects.update_or_create(
                session=session, date=dt, staff_type=stype,
                defaults={
                    'total_staff': total,
                    'present_count': counts['P'],
                    'absent_count': counts['A'],
                    'leave_count': counts['L'],
                    'late_count': counts['T'],
                    'halfday_count': counts['H'],
                    'is_locked': False,
                    'marked_by': who,
                    'marked_at': now,
                    'updated_at': now,
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
def sa_lock(request):
    try:
        try:
            b = json.loads(request.body)
        except Exception:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'})
        session = b.get('session') or current_session()
        stype = (b.get('type') or 'all').strip()
        dt = parse_date(b.get('date', ''))
        lock = StaffAttendanceLock.objects.filter(
            session=session, date=dt, staff_type=stype
        ).first()
        if not lock:
            return JsonResponse({'success': False, 'error': 'Please save the attendance first'})
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
def sa_report(request):
    try:
        session = request.GET.get('session') or current_session()
        stype = (request.GET.get('type') or 'all').strip()
        desig = (request.GET.get('desig') or 'all').strip()
        ym = (request.GET.get('month') or '').strip() or _date.today().strftime('%Y-%m')
        ensure_staff_auto_absent(session)

        try:
            y, m = map(int, ym.split('-'))
            if not (1 <= m <= 12):
                raise ValueError
        except Exception:
            y, m = _date.today().year, _date.today().month

        days_in_month = calendar.monthrange(y, m)[1]
        today = _date.today()
        cfg = get_setting(session)
        working = set(cfg['working_days'])
        hols = holiday_map(session, y, m)

        day_meta = []
        for d in range(1, days_in_month + 1):
            dd = _date(y, m, d)
            iso = dd.isoformat()
            weekly_off = dd.isoweekday() not in working
            is_hol = iso in hols
            day_meta.append({
                'd': d, 'iso': iso, 'wd': dd.strftime('%a')[:2],
                'off': weekly_off or is_hol,
                'holiday': hols.get(iso, 'Weekly Off' if weekly_off else ''),
                'is_holiday': is_hol, 'future': dd > today,
            })

        # report: saari staff, cells mein joining se pehle '-'
        staff_full = []
        for obj, typ in _iter_staff_objects(stype):
            row = _obj_to_row(obj, typ)
            row['_join'] = staff_joining_date(obj)
            staff_full.append(row)
        if desig and desig != 'all':
            staff_full = [x for x in staff_full if x['designation'] == desig]

        working_days_count = len([d for d in day_meta if not d['off'] and not d['future']])

        if not staff_full:
            return JsonResponse({
                'success': True,
                'month_label': _date(y, m, 1).strftime('%B %Y'),
                'days': day_meta, 'rows': [],
                'summary': {
                    'staff': 0, 'working_days': working_days_count,
                    'marked_days': 0, 'auto_days': 0, 'avg_percentage': 0,
                    'below_min': 0, 'min_percentage': cfg['min_percentage'],
                    'total_late': 0,
                },
                'message': 'No staff members found',
            })

        recs = {}
        try:
            for a in StaffAttendance.objects.filter(
                session=session, date__year=y, date__month=m
            ).values('emp_id', 'date', 'status', 'marked_by'):
                recs[(str(a['emp_id']), a['date'].isoformat())] = (
                    a['status'], (a['marked_by'] or '').lower()
                )
        except Exception as e:
            print('WARNING - report recs:', e)

        marked_iso, auto_iso = set(), set()
        try:
            for d, by in StaffAttendanceLock.objects.filter(
                session=session, date__year=y, date__month=m
            ).values_list('date', 'marked_by'):
                marked_iso.add(d.isoformat())
                if (by or '').lower() == AUTO_MARKER:
                    auto_iso.add(d.isoformat())
        except Exception as e:
            print('WARNING - report locks:', e)

        rows = []
        for s in staff_full:
            cells, c, work = [], {k: 0 for k in STATUS_KEYS}, 0
            join = s.get('_join')
            for dm in day_meta:
                dd = _date.fromisoformat(dm['iso'])
                if dm['off']:
                    cells.append('O')
                    continue
                if dm['future']:
                    cells.append('-')
                    continue
                if join and dd < join:
                    cells.append('-')
                    continue
                rec = recs.get((s['emp_id'], dm['iso']))
                if rec:
                    st, by = rec
                    cells.append('U' if (st == 'A' and by == AUTO_MARKER) else st)
                    c[st] += 1
                    work += 1
                    continue
                if dm['iso'] in marked_iso:
                    cells.append('N')
                    c['A'] += 1
                    work += 1
                else:
                    cells.append('-')

            eff = c['P'] + c['T'] + c['H'] * 0.5
            pct = round(eff / work * 100, 1) if work else 0
            rows.append({
                'emp_id': s['emp_id'], 'name': s['name'],
                'designation': s['designation'], 'type': s['type'],
                'cells': cells,
                'P': c['P'], 'A': c['A'], 'L': c['L'], 'T': c['T'], 'H': c['H'],
                'working': work, 'pct': pct,
            })

        tot = len(rows)
        avg = round(sum(r['pct'] for r in rows) / tot, 1) if tot else 0
        below = len([r for r in rows if r['working'] and r['pct'] < cfg['min_percentage']])
        return JsonResponse({
            'success': True,
            'month_label': _date(y, m, 1).strftime('%B %Y'),
            'days': day_meta, 'rows': rows,
            'summary': {
                'staff': tot,
                'working_days': working_days_count,
                'marked_days': len(marked_iso),
                'auto_days': len(auto_iso),
                'avg_percentage': avg,
                'below_min': below,
                'min_percentage': cfg['min_percentage'],
                'total_late': sum(r['T'] for r in rows),
            }
        })
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f'Report error: {e}'})


@require_GET
def sa_today_summary(request):
    try:
        session = request.GET.get('session') or current_session()
        dt = parse_date(request.GET.get('date', ''))
        ensure_staff_auto_absent(session)
        recs = {str(a.emp_id): a for a in StaffAttendance.objects.filter(session=session, date=dt)}
        staff = build_staff_list('all', on_date=dt)
        c = {k: 0 for k in STATUS_KEYS}
        absent_list, late_list = [], []
        for s in staff:
            a = recs.get(s['emp_id'])
            if not a:
                continue
            if a.status in c:
                c[a.status] += 1
            if a.status == 'A':
                absent_list.append({'name': s['name'], 'designation': s['designation']})
            if a.status == 'T':
                late_list.append({'name': s['name'], 'in': t_str(a.check_in)})
        total = len(staff)
        marked = sum(c.values())
        eff = c['P'] + c['T'] + c['H'] * 0.5
        return JsonResponse({
            'success': True, 'date': dt.isoformat(),
            'total_staff': total, 'marked': marked, 'pending': total - marked,
            'counts': c, 'percentage': round(eff / total * 100, 1) if total else 0,
            'absent_list': absent_list, 'late_list': late_list,
        })
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@require_GET
def sa_staff_history(request):
    try:
        emp = (request.GET.get('emp_id') or '').strip()
        session = request.GET.get('session') or current_session()
        if not emp:
            return JsonResponse({'success': False, 'error': 'emp_id is required'})
        qs = StaffAttendance.objects.filter(session=session, emp_id=emp).order_by('-date')
        recs = [{
            'date': a.date.isoformat(), 'day': a.date.strftime('%a'),
            'status': a.status, 'label': STATUS_LABEL.get(a.status, a.status),
            'check_in': t_str(a.check_in), 'check_out': t_str(a.check_out),
            'leave_type': LEAVE_TYPES.get(a.leave_type, a.leave_type or ''),
            'remarks': a.remarks or '',
            'auto': (a.marked_by or '').lower() == AUTO_MARKER,
        } for a in qs[:200]]
        c = {k: 0 for k in STATUS_KEYS}
        for a in qs:
            if a.status in c:
                c[a.status] += 1
        total = sum(c.values())
        eff = c['P'] + c['T'] + c['H'] * 0.5
        first = qs.first()
        return JsonResponse({
            'success': True,
            'staff': {
                'emp_id': emp,
                'name': first.staff_name if first else '',
                'designation': first.designation if first else '',
                'type': first.staff_type if first else '',
            },
            'records': recs, 'counts': c, 'total_days': total,
            'percentage': round(eff / total * 100, 1) if total else 0,
            'deduction_days': c['A'] + (c['H'] * 0.5),
        })
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})
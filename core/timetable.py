import json
from datetime import datetime, time
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt

from .models import (
    SchoolProfile, ClassDefination, SubjectDefination,
    CoreTeacher, TimetableSlot, TimetablePeriod, TimetableDay,
    AcademicSession,
)
from .user_rights import get_user_module_permissions

DEFAULT_DAY_NAMES = {
    1: 'Monday', 2: 'Tuesday', 3: 'Wednesday',
    4: 'Thursday', 5: 'Friday', 6: 'Saturday', 0: 'Sunday'
}


def get_school():
    return SchoolProfile.objects.filter(is_active=True).first()


def ensure_default_timetable_data():
    """
    Agar MSSQL database mein TimetableDay ya TimetablePeriod khali hon, 
    toh automatically default Working Days aur Periods insert karta hai.
    """
    try:
        # 1. Check & Seed Days
        if not TimetableDay.objects.exists():
            days_setup = [
                (1, 'Monday', True, 8),
                (2, 'Tuesday', True, 8),
                (3, 'Wednesday', True, 8),
                (4, 'Thursday', True, 8),
                (5, 'Friday', True, 8),
                (6, 'Saturday', True, 8),
            ]
            for d_val, name, working, last_p in days_setup:
                TimetableDay.objects.create(
                    day_of_week=d_val,
                    name=name,
                    is_working=working,
                    last_period_no=last_p
                )

        # 2. Check & Seed Periods
        if not TimetablePeriod.objects.exists():
            default_periods = [
                (1, 1, 'Period 1', time(8, 0), time(8, 45), False, True),
                (2, 2, 'Period 2', time(8, 45), time(9, 30), False, True),
                (3, 3, 'Period 3', time(9, 30), time(10, 15), False, True),
                (4, None, 'Break / Recess', time(10, 15), time(10, 45), True, True),
                (5, 4, 'Period 4', time(10, 45), time(11, 30), False, True),
                (6, 5, 'Period 5', time(11, 30), time(12, 15), False, True),
                (7, 6, 'Period 6', time(12, 15), time(13, 00), False, True),
                (8, 7, 'Period 7', time(13, 00), time(13, 40), False, True),
                (9, 8, 'Period 8', time(13, 40), time(14, 20), False, True),
            ]
            for sort_o, p_no, p_name, st, et, brk, act in default_periods:
                TimetablePeriod.objects.create(
                    sort_order=sort_o,
                    period_no=p_no,
                    name=p_name,
                    start_time=st,
                    end_time=et,
                    is_break=brk,
                    is_active=act
                )
    except Exception as e:
        print("Timetable Auto-Seeding Error:", e)


def get_academic_sessions_data():
    try:
        all_sessions = list(
            AcademicSession.objects.all().order_by('-id').values_list('session_name', flat=True)
        )
        current_sess = AcademicSession.objects.filter(is_current=True).order_by('-id').first()

        if current_sess:
            current_name = current_sess.session_name
        elif all_sessions:
            current_name = all_sessions[0]
        else:
            y = datetime.now().year
            current_name = f"{y}-{y+1}"

        if not all_sessions:
            all_sessions = [current_name]
        elif current_name not in all_sessions:
            all_sessions.insert(0, current_name)

        return current_name, all_sessions
    except Exception as e:
        y = datetime.now().year
        return f"{y}-{y+1}", [f"{y}-{y+1}"]


def format_periods():
    ensure_default_timetable_data()
    qs = TimetablePeriod.objects.filter(is_active=True).order_by('sort_order')
    return [
        {
            'period_no': p.period_no,
            'name': p.name,
            'start_time': p.start_time.strftime('%H:%M') if p.start_time else '',
            'end_time': p.end_time.strftime('%H:%M') if p.end_time else '',
            'is_break': p.is_break,
        }
        for p in qs
    ]


def format_days():
    ensure_default_timetable_data()
    qs = TimetableDay.objects.all().order_by('day_of_week')
    return [
        {
            'day': d.day_of_week,
            'name': d.name,
            'is_working': d.is_working,
            'last_period_no': d.last_period_no,
        }
        for d in qs
    ]


def build_off(periods, days):
    off = {}
    all_period_nos = [p['period_no'] for p in periods if not p['is_break'] and p['period_no']]
    max_p = max(all_period_nos) if all_period_nos else 0
    for d in days:
        if d['is_working'] and d['last_period_no'] and d['last_period_no'] < max_p:
            off_list = [pn for pn in all_period_nos if pn > d['last_period_no']]
            if off_list:
                off[d['day']] = off_list
    return off


def day_name(day_val):
    d = TimetableDay.objects.filter(day_of_week=day_val).first()
    if d and d.name:
        return d.name
    return DEFAULT_DAY_NAMES.get(day_val, f'Day {day_val}')


def teacher_name(emp_id):
    t = CoreTeacher.objects.filter(emp_id=emp_id).first()
    return t.name if t else emp_id


# ─────────────────────────────────────────
# PAGE
# ─────────────────────────────────────────

def timetable_page(request):
    # ================= RIGHTS CHECK: VIEW =================
    perms = get_user_module_permissions(request.user, "timetable")
    if not perms.get('can_view'):
        messages.error(request, "Access Denied: You do not have permission to view the Timetable.")
        # ✅ Jahan se click kiya wahi wapas rahega (e.g. teacher dashboard)
        fallback = 'teacher_dashboard' if request.session.get('user_role') == 'Teacher' else 'dashboard'
        return redirect(request.META.get('HTTP_REFERER') or fallback)

    school = get_school()
    current_session, sessions = get_academic_sessions_data()

    classes = ClassDefination.objects.all().order_by('class_field', 'section')
    class_sections = list(classes.values('class_field', 'section', 'room_number'))
    teachers = list(
        CoreTeacher.objects.filter(is_active=True)
        .values('emp_id', 'name', 'subject').order_by('name')
    )
    subjects = list(SubjectDefination.objects.all().values_list('subject_name', flat=True).distinct())

    periods = format_periods()
    days = format_days()
    off = build_off(periods, days)

    context = {
        'school': school,
        'default_session': current_session,
        'sessions': json.dumps(sessions),
        'class_sections': json.dumps(class_sections),
        'teachers_json': json.dumps(teachers),
        'subjects_json': json.dumps(subjects),
        'periods_json': json.dumps(periods),
        'days_json': json.dumps(days),
        'off_json': json.dumps(off),
        'perms': perms,
    }
    return render(request, 'timetable.html', context)


# ─────────────────────────────────────────
# GRID DATA
# ─────────────────────────────────────────

@require_GET
def tt_data(request):
    perms = get_user_module_permissions(request.user, "timetable")
    if not perms.get('can_view'):
        return JsonResponse({'success': False, 'error': 'Permission Denied'}, status=403)

    current_sess, _ = get_academic_sessions_data()
    session = request.GET.get('session') or current_sess
    view    = request.GET.get('view', 'class')
    cls     = request.GET.get('class')
    sec     = request.GET.get('section')
    emp_id  = request.GET.get('emp_id')

    periods = format_periods()
    days    = format_days()
    off     = build_off(periods, days)
    slots   = []

    if view == 'class':
        qs = TimetableSlot.objects.filter(session=session, class_field=cls, section=sec)
        for s in qs:
            slots.append({
                'key': f"{s.day_of_week}|{s.period_no}",
                'subject': s.subject,
                'emp_id': s.emp_id,
                'room': s.room or '',
            })
    else:
        qs = TimetableSlot.objects.filter(session=session, emp_id=emp_id)
        for s in qs:
            slots.append({
                'key': f"{s.day_of_week}|{s.period_no}",
                'subject': s.subject,
                'emp_id': s.emp_id,
                'room': s.room or '',
                'class': s.class_field,
                'section': s.section,
            })

    return JsonResponse({
        'success': True,
        'periods': periods,
        'days': days,
        'off': off,
        'slots': slots,
    })


# ─────────────────────────────────────────
# TEACHER BUSY MAP
# ─────────────────────────────────────────

@require_GET
def tt_busy(request):
    perms = get_user_module_permissions(request.user, "timetable")
    if not perms.get('can_view'):
        return JsonResponse({'success': True, 'busy': {}})

    current_sess, _ = get_academic_sessions_data()
    session = request.GET.get('session') or current_sess
    cls     = request.GET.get('class')
    sec     = request.GET.get('section')

    if not session:
        return JsonResponse({'success': True, 'busy': {}})

    qs = TimetableSlot.objects.filter(session=session).exclude(emp_id='').exclude(emp_id=None)
    if cls and sec:
        qs = qs.exclude(class_field=cls, section=sec)

    busy = {}
    for s in qs:
        busy[f"{s.emp_id}|{s.day_of_week}|{s.period_no}"] = {
            'class': s.class_field,
            'section': s.section,
            'subject': s.subject,
        }

    return JsonResponse({'success': True, 'busy': busy})


# ─────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────

@csrf_exempt
@require_POST
def tt_save(request):
    perms = get_user_module_permissions(request.user, "timetable")

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})

    current_sess, _ = get_academic_sessions_data()
    session   = data.get('session') or current_sess
    cls       = data.get('class')
    sec       = data.get('section')
    items     = data.get('items', [])
    overwrite = data.get('overwrite', False)
    is_delete = data.get('delete', False)

    if is_delete and not perms.get('can_delete') and not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission Denied: You cannot delete timetable slots'}, status=403)
    elif not is_delete and not perms.get('can_add') and not perms.get('can_edit') and not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission Denied: You cannot add or modify timetable slots'}, status=403)

    if not session or not cls or not sec:
        return JsonResponse({'success': False, 'error': 'Missing class/session/section'})
    if not items:
        return JsonResponse({'success': False, 'error': 'No items received'})

    added = skipped = deleted = 0
    conflicts = []
    now = datetime.now()

    seen_teacher_slot = {}

    for item in items:
        day = item.get('day')
        period = item.get('period')
        if day is None or period is None:
            continue

        filter_kwargs = {
            'session': session,
            'class_field': cls,
            'section': sec,
            'day_of_week': day,
            'period_no': period,
        }

        if is_delete or item.get('delete'):
            if not perms.get('can_delete') and not request.user.is_superuser:
                continue
            deleted += TimetableSlot.objects.filter(**filter_kwargs).delete()[0]
            continue

        subject = item.get('subject')
        emp_id  = (item.get('emp_id') or '').strip()
        room    = item.get('room') or ''

        if not subject:
            continue

        if emp_id:
            k = f"{emp_id}|{day}|{period}"
            if k in seen_teacher_slot:
                conflicts.append({
                    'day': day, 'period': period,
                    'day_name': day_name(day),
                    'teacher': teacher_name(emp_id),
                    'class': cls, 'section': sec,
                    'subject': seen_teacher_slot[k],
                    'reason': 'duplicate in this request',
                })
                continue
            seen_teacher_slot[k] = subject

        if emp_id:
            clash = (TimetableSlot.objects
                     .filter(session=session, day_of_week=day,
                             period_no=period, emp_id=emp_id)
                     .exclude(class_field=cls, section=sec)
                     .first())
            if clash:
                conflicts.append({
                    'day': day, 'period': period,
                    'day_name': day_name(day),
                    'teacher': teacher_name(emp_id),
                    'class': clash.class_field,
                    'section': clash.section,
                    'subject': clash.subject,
                    'reason': 'teacher already booked',
                })
                continue

        exists = TimetableSlot.objects.filter(**filter_kwargs).exists()
        if exists and not overwrite:
            skipped += 1
            continue

        TimetableSlot.objects.update_or_create(
            **filter_kwargs,
            defaults={
                'subject': subject,
                'emp_id': emp_id,
                'room': room,
                'created_at': now,
                'updated_at': now,
            }
        )
        added += 1

    if conflicts and added == 0 and deleted == 0:
        first = conflicts[0]
        return JsonResponse({
            'success': False,
            'error': (f"⛔ Clash: {first['teacher']} is already teaching "
                      f"{first['subject']} to Class {first['class']}-{first['section']} "
                      f"on {first['day_name']} · Period {first['period']}."),
            'conflicts': conflicts,
        })

    if is_delete:
        msg = f"Deleted {deleted} slot(s)"
    else:
        msg = f"Saved {added}"
        if skipped:
            msg += f", skipped {skipped} (already filled)"
        if conflicts:
            msg += f", {len(conflicts)} clash(es) blocked"

    return JsonResponse({
        'success': True,
        'message': msg,
        'conflicts': conflicts,
    })


# ─────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────

def timetable_settings(request):
    perms = get_user_module_permissions(request.user, "timetable")
    if not perms.get('can_edit') and not request.user.is_superuser:
        messages.error(request, "Access Denied: Only administrators can configure timetable settings.")
        return redirect('timetable_page')

    school = get_school()
    return render(request, 'timetable_settings.html', {'school': school, 'perms': perms})


@require_GET
def tt_settings_data(request):
    ensure_default_timetable_data()
    periods = []
    for p in TimetablePeriod.objects.all().order_by('sort_order'):
        periods.append({
            'id': p.id, 'sort_order': p.sort_order, 'period_no': p.period_no,
            'name': p.name,
            'start_time': p.start_time.strftime('%H:%M') if p.start_time else '',
            'end_time': p.end_time.strftime('%H:%M') if p.end_time else '',
            'is_break': p.is_break, 'is_active': p.is_active,
        })
    days = []
    for d in TimetableDay.objects.all().order_by('day_of_week'):
        days.append({
            'id': d.id, 'day': d.day_of_week, 'name': d.name,
            'is_working': d.is_working, 'last_period_no': d.last_period_no,
        })
    return JsonResponse({'success': True, 'periods': periods, 'days': days})


@csrf_exempt
@require_POST
def tt_save_periods(request):
    perms = get_user_module_permissions(request.user, "timetable")
    if not perms.get('can_edit') and not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission Denied'}, status=403)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})

    periods = data.get('periods', [])
    if not periods:
        return JsonResponse({'success': False, 'error': 'No periods received'})

    TimetablePeriod.objects.all().delete()
    period_counter = 0
    for i, p in enumerate(periods, start=1):
        name = (p.get('name') or '').strip()
        start = p.get('start_time'); end = p.get('end_time')
        is_break = bool(p.get('is_break', False))
        is_active = bool(p.get('is_active', True))
        if not name or not start or not end:
            continue
        if is_break:
            period_no = None
        else:
            period_counter += 1
            period_no = period_counter
        TimetablePeriod.objects.create(
            sort_order=i, period_no=period_no, name=name,
            start_time=start, end_time=end,
            is_break=is_break, is_active=is_active,
        )
    return JsonResponse({'success': True, 'message': 'Periods saved successfully'})


@csrf_exempt
@require_POST
def tt_save_days(request):
    perms = get_user_module_permissions(request.user, "timetable")
    if not perms.get('can_edit') and not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission Denied'}, status=403)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})

    days = data.get('days', [])
    if not days:
        return JsonResponse({'success': False, 'error': 'No days received'})

    for d in days:
        day_val = d.get('day')
        if day_val is None:
            continue
        TimetableDay.objects.update_or_create(
            day_of_week=day_val,
            defaults={
                'name': d.get('name', ''),
                'is_working': bool(d.get('is_working', True)),
                'last_period_no': d.get('last_period_no') or None,
            }
        )
    return JsonResponse({'success': True, 'message': 'Days saved successfully'})
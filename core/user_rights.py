import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db import connection
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.views.decorators.http import require_POST, require_GET
from django.db import transaction
from django.utils import timezone

from .models import (
    AcademicSession,
    ClassDefination,
    CoreTeacher,
    CoreStaff,
    CoreStudent as Student,
    CoreUserModulePermission,
)


def get_active_classes():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT [class]
            FROM Class_defination
            WHERE status = 'Active'
            ORDER BY [class]
        """)
        return [row[0] for row in cursor.fetchall() if row[0]]


def get_user_module_permissions(user, module_name="students"):
    if not user or not user.is_authenticated:
        return {'can_view': False, 'can_add': False, 'can_edit': False, 'can_delete': False, 'can_print': False}

    if user.is_superuser:
        return {'can_view': True, 'can_add': True, 'can_edit': True, 'can_delete': True, 'can_print': True}

    username = user.username

    # ---------- STUDENT ----------
    student = Student.objects.filter(
        Q(roll_no__iexact=username) | Q(reg_no__iexact=username),
        is_active=True
    ).first()
    if student:
        cls = (student.student_class or '').strip()
        sec = (student.section or '').strip()

        for (t, s) in [(cls, sec), (cls, ''), ('ALL', '')]:
            p = _db_perm('student', t, s, module_name)
            if p:
                if module_name in ['promote', 'passouts'] and p.get('can_view'):
                    p.update({'can_add': True, 'can_edit': True, 'can_delete': True, 'can_print': True})
                return p

        return {
            'can_view': module_name in ['dashboard', 'student_dashboard', 'results', 'notice', 'timetable'],
            'can_add': False, 'can_edit': False, 'can_delete': False,
            'can_print': module_name in ['dashboard', 'student_dashboard', 'results', 'notice', 'timetable']
        }

    # ---------- TEACHER ----------
    teacher = CoreTeacher.objects.filter(emp_id__iexact=username, is_active=True).first()
    if teacher:
        for t in [f"T-{teacher.id}", "ROLE_TEACHER"]:
            p = _db_perm('staff', t, '', module_name)
            if p:
                if module_name in ['promote', 'passouts'] and p.get('can_view'):
                    p.update({'can_add': True, 'can_edit': True, 'can_delete': True, 'can_print': True})
                return p

        allowed_modules = ['dashboard', 'teacher_dashboard', 'students', 'timetable', 'exam', 'results', 'attendance', 'notice']
        can_view = module_name in allowed_modules
        can_act = module_name in ['exam', 'results', 'attendance']
        return {
            'can_view': can_view,
            'can_add': can_act,
            'can_edit': can_act,
            'can_delete': False,
            'can_print': can_view
        }

    # ---------- STAFF ----------
    staff = CoreStaff.objects.filter(emp_id__iexact=username, is_active=True).first()
    if staff:
        role_target = f"ROLE_{(staff.role or '').strip().upper()}"
        for t in [f"S-{staff.id}", role_target]:
            p = _db_perm('staff', t, '', module_name)
            if p:
                if module_name in ['promote', 'passouts'] and p.get('can_view'):
                    p.update({'can_add': True, 'can_edit': True, 'can_delete': True, 'can_print': True})
                return p

    is_staff_user = user.is_staff
    return {
        'can_view': is_staff_user,
        'can_add': is_staff_user,
        'can_edit': is_staff_user,
        'can_delete': False,
        'can_print': is_staff_user
    }


def _db_perm(mode, target, section, module_name):
    row = CoreUserModulePermission.objects.filter(
        mode=mode, target=target, section=section, module_name=module_name
    ).values(
        'can_view', 'can_add', 'can_edit', 'can_delete', 'can_print'
    ).first()
    return row


def user_rights_view(request):
    curr_sess = AcademicSession.objects.filter(is_current=True).first()
    academic_year = curr_sess.session_name if curr_sess else "2026-2027"

    available_classes = get_active_classes()
    total_students_count = Student.objects.filter(is_active=True).count()

    teachers = CoreTeacher.objects.all().order_by('name')
    staff_members = CoreStaff.objects.all().order_by('name')

    distinct_roles = list(
        CoreStaff.objects.exclude(role__isnull=True)
        .exclude(role='')
        .values_list('role', flat=True)
        .distinct()
    )

    context = {
        'academic_year': academic_year,
        'available_classes': available_classes,
        'total_students_count': total_students_count,
        'teachers': teachers,
        'staff_members': staff_members,
        'distinct_roles': distinct_roles,
    }
    return render(request, "user_rights.html", context)


def get_class_student_count_api(request):
    class_name = request.GET.get('class', '').strip()
    section_name = request.GET.get('section', '').strip()

    qs = Student.objects.filter(is_active=True)
    if class_name and class_name != 'ALL':
        qs = qs.filter(student_class__iexact=class_name)
    if section_name:
        qs = qs.filter(section__iexact=section_name)

    return JsonResponse({'count': qs.count()})


# ✅ NAYA ENDPOINT: Database se saved permissions fetch karega
@require_GET
def get_user_rights_api(request):
    mode = (request.GET.get('mode') or '').strip()
    target = (request.GET.get('target') or '').strip()
    section = (request.GET.get('section') or '').strip() if mode == 'student' else ''

    if not mode or not target:
        return JsonResponse({'success': False, 'permissions': {}})

    rows = CoreUserModulePermission.objects.filter(
        mode=mode, target=target, section=section
    ).values('module_name', 'can_view', 'can_add', 'can_edit', 'can_delete', 'can_print')

    perms_dict = {}
    for r in rows:
        perms_dict[r['module_name']] = {
            'can_view': r['can_view'],
            'can_add': r['can_add'],
            'can_edit': r['can_edit'],
            'can_delete': r['can_delete'],
            'can_print': r['can_print'],
        }

    return JsonResponse({'success': True, 'permissions': perms_dict})


@csrf_exempt
@require_POST
def save_user_rights_api(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        mode = (data.get('mode') or '').strip()
        target = (data.get('target') or '').strip()
        section = (data.get('section') or '').strip() if mode == 'student' else ''
        permissions = data.get('permissions') or {}

        if mode not in ['student', 'staff']:
            return JsonResponse({'success': False, 'error': 'Invalid mode'}, status=400)
        if not target:
            return JsonResponse({'success': False, 'error': 'Target is required'}, status=400)

        now = timezone.now()

        with transaction.atomic():
            CoreUserModulePermission.objects.filter(
                mode=mode, target=target, section=section
            ).delete()

            bulk = []
            for module_name, p in permissions.items():
                v = bool(p.get('can_view'))
                a = bool(p.get('can_add'))
                e = bool(p.get('can_edit'))
                d = bool(p.get('can_delete'))
                pr = bool(p.get('can_print'))

                if module_name in ['promote', 'passouts'] and v:
                    a = e = d = pr = True

                bulk.append(CoreUserModulePermission(
                    mode=mode,
                    target=target,
                    section=section,
                    module_name=module_name,
                    can_view=v,
                    can_add=a,
                    can_edit=e,
                    can_delete=d,
                    can_print=pr,
                    updated_by=request.user.username,
                    updated_at=now
                ))

            CoreUserModulePermission.objects.bulk_create(bulk, batch_size=200)

        return JsonResponse({'success': True, 'message': 'Permissions saved successfully!'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
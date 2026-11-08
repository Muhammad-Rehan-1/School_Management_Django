import json
import re
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.db import transaction, connection
from django.db.models import Q
from .user_rights import get_user_module_permissions
from django.contrib import messages
from .models import CoreStudent as Student, ClassDefination, AcademicSession, PromotionDraft, StudentAlumni



def get_academic_classes():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT [class] 
            FROM Class_defination 
            WHERE status = 'Active' 
            ORDER BY [class]
        """)
        return [row[0] for row in cursor.fetchall()]

def get_class_sections(class_name):
    if not class_name or 'graduated' in class_name.lower() or 'passout' in class_name.lower():
        return []
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT RTRIM(LTRIM(section)) 
            FROM Class_defination 
            WHERE [class] = %s AND status = 'Active' 
            ORDER BY RTRIM(LTRIM(section))
        """, [class_name])
        return [row[0] for row in cursor.fetchall()]

def get_session_info():
    curr = AcademicSession.objects.filter(is_current=True).first()
    curr_name = curr.session_name if curr else "2026-2027"

    parts = curr_name.split('-')
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        target_name = f"{int(parts[0])+1}-{int(parts[1])+1}"
    else:
        target_name = "2027-2028"
    return curr_name, target_name

def calculate_next_roll_no(class_name, section_name):
    """Class aur Section ke liye clean available roll number nikalta hai"""
    target_prefix = f"{class_name}-{section_name}-"
    max_num = 0
    for s in Student.objects.filter(student_class__iexact=class_name, section__iexact=section_name):
        val = str(s.roll_no or '').replace(target_prefix, '').strip()
        if val.isdigit():
            max_num = max(max_num, int(val))
    return f"{target_prefix}{max_num + 1}"

def get_student_remaining_dues(student_id):
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT ISNULL(SUM(balance), 0)
                FROM fee_challan
                WHERE student_id = %s AND status != 'Paid'
            """, [student_id])
            row = cursor.fetchone()
            return Decimal(row[0]) if row and row[0] is not None else Decimal('0.00')
    except Exception:
        return Decimal('0.00')

def promote_students_view(request):
    perms = get_user_module_permissions(request.user, "promote")
    if not perms.get("can_view"):
        messages.error(request, "Access Denied: You do not have permission to view Promote Students.")
        return redirect("dashboard")
    
    current_class = request.GET.get('current_class', '').strip()
    current_section = request.GET.get('current_section', '').strip()
    target_class = request.GET.get('target_class', '').strip()
    target_section = request.GET.get('target_section', '').strip()

    curr_session, target_session = get_session_info()
    classes = get_academic_classes()
    current_sections = get_class_sections(current_class)
    target_sections = get_class_sections(target_class)

    students = []
    staged_student_ids = []
    if current_class and current_section:
        students = Student.objects.filter(
            student_class__iexact=current_class,
            section__iexact=current_section,
            is_active=True
        ).order_by('roll_no', 'id')

        staged_student_ids = list(PromotionDraft.objects.filter(
            from_class__iexact=current_class,
            from_section__iexact=current_section
        ).values_list('student_id', flat=True))

    all_drafts = PromotionDraft.objects.select_related('student').all().order_by('to_class', 'new_roll_no')
    drafted_classes = PromotionDraft.objects.values('from_class', 'from_section', 'to_class', 'to_section').distinct()

    context = {
        'curr_session': curr_session,
        'target_session': target_session,
        'classes': classes,
        'current_class': current_class,
        'current_section': current_section,
        'target_class': target_class,
        'target_section': target_section,
        'current_sections': current_sections,
        'target_sections': target_sections,
        'students': students,
        'staged_student_ids': staged_student_ids,
        'all_drafts': all_drafts,
        'drafted_classes': drafted_classes,
        'total_drafted_count': all_drafts.count(),
    }
    return render(request, "promote_students.html", context)


@transaction.atomic
def save_class_draft_api(request):
    if request.method != "POST":
        return JsonResponse({'success': False, 'message': 'Invalid method'}, status=400)
    perms = get_user_module_permissions(request.user, "promote")
    if not (perms.get("can_add") or perms.get("can_edit")):
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)

    try:
        data = json.loads(request.body)
        curr_class = data.get('current_class', '').strip()
        curr_section = data.get('current_section', '').strip()
        target_class = data.get('target_class', '').strip()
        target_section = data.get('target_section', '').strip()
        promoted_ids = set(data.get('promoted_student_ids', []))

        _, target_session = get_session_info()

        PromotionDraft.objects.filter(from_class__iexact=curr_class, from_section__iexact=curr_section).delete()

        students = Student.objects.filter(
            student_class__iexact=curr_class,
            section__iexact=curr_section,
            is_active=True
        ).order_by('roll_no', 'id')

        is_graduating = (target_class.strip().lower() == 'graduated / passout')

        target_prefix = f"{target_class}-{target_section}-" if not is_graduating else "PASSOUT-"
        drafted_max = 0
        for d in PromotionDraft.objects.filter(to_class__iexact=target_class, to_section__iexact=target_section):
            val = str(d.new_roll_no).replace(target_prefix, '').strip()
            if val.isdigit():
                drafted_max = max(drafted_max, int(val))

        target_existing_max = 0
        if not is_graduating:
            for s in Student.objects.filter(student_class__iexact=target_class, section__iexact=target_section):
                val = str(s.roll_no or '').replace(target_prefix, '').strip()
                if val.isdigit():
                    target_existing_max = max(target_existing_max, int(val))

        curr_prefix = f"{curr_class}-{curr_section}-"
        curr_max = 0
        for s in Student.objects.filter(student_class__iexact=curr_class, section__iexact=curr_section):
            val = str(s.roll_no or '').replace(curr_prefix, '').strip()
            if val.isdigit():
                curr_max = max(curr_max, int(val))

        prom_counter = max(drafted_max, target_existing_max) + 1
        repeat_counter = curr_max + 1

        draft_entries = []
        for s in students:
            is_prom = str(s.id) in promoted_ids or s.id in promoted_ids
            if is_prom:
                if is_graduating:
                    new_roll = "ALUMNI"
                    dest_cls = "Graduated / Passout"
                    dest_sec = "None"
                else:
                    new_roll = f"{target_class}-{target_section}-{prom_counter}"
                    dest_cls = target_class
                    dest_sec = target_section
                    prom_counter += 1
            else:
                new_roll = f"{curr_class}-{curr_section}-{repeat_counter}"
                dest_cls = curr_class
                dest_sec = curr_section
                repeat_counter += 1

            draft_entries.append(PromotionDraft(
                student=s,
                target_session=target_session,
                from_class=curr_class,
                from_section=curr_section,
                old_roll_no=s.roll_no or '—',
                to_class=dest_cls,
                to_section=dest_sec,
                new_roll_no=new_roll,
                is_promoted=is_prom
            ))

        PromotionDraft.objects.bulk_create(draft_entries)
        return JsonResponse({'success': True, 'count': len(draft_entries)})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


def clear_all_drafts(request):
    perms = get_user_module_permissions(request.user, "promote")
    if not perms.get("can_edit"):
        messages.error(request, "Access Denied.")
        return redirect("promote_students")

    if request.method == "POST":
        PromotionDraft.objects.all().delete()
        messages.success(request, "Promotion staging draft cleared successfully.")
    return redirect('promote_students')


@transaction.atomic
def execute_full_session_promotion(request):
    """
    Apply all staged PromotionDraft rows to live students.

    - Normal promoted/repeater students remain is_active=True.
    - Only students staged to 'Graduated / Passout' become Alumni and are deactivated.
    - Session switch is OPTIONAL (controlled by POST switch_session=1).
      If switch_session is NOT checked: promotions apply, but AcademicSession.is_current does NOT change.
    """
    perms = get_user_module_permissions(request.user, "promote")
    if not perms.get("can_edit"):
        messages.error(request, "Access Denied.")
        return redirect("promote_students")

    if request.method != "POST":
        return redirect("promote_students")

    switch_session = request.POST.get("switch_session") == "1"
    today = timezone.localdate()

    drafts = PromotionDraft.objects.select_related("student").all()
    if not drafts.exists():
        messages.error(request, "No classes are staged in draft. Please stage classes first.")
        return redirect("promote_students")

    curr_session, target_session = get_session_info()

    try:
        # 1) Apply drafts to students
        for d in drafts:
            student = d.student
            to_cls = (d.to_class or "").strip().lower()

            if to_cls == "graduated / passout":
                dues = get_student_remaining_dues(student.id)

                StudentAlumni.objects.create(
                    student=student,
                    reg_no=student.reg_no,
                    student_name=student.name,
                    father_name=student.father_name,
                    passed_class=d.from_class,
                    passed_section=d.from_section,
                    passed_session=curr_session,
                    remaining_dues=dues,
                    remarks="Graduated upon promotion execution",
                )

                # deactivate student from active list
                student.is_active = False
                student.student_class = "Graduated"
                student.section = None
                student.roll_no = "ALUMNI"
                student.save(update_fields=["is_active", "student_class", "section", "roll_no"])

            else:
                # promoted OR repeater (both remain active)
                student.student_class = d.to_class
                student.section = d.to_section
                student.roll_no = d.new_roll_no
                student.is_active = True
                student.save(update_fields=["student_class", "section", "roll_no", "is_active"])

        applied_count = drafts.count()

        # 2) Optional: Switch session only if user agreed
        if switch_session:
            old = AcademicSession.objects.filter(is_current=True).first()
            if old:
                old.is_current = False
                # end_date set to one day before switch (if you want boundaries)
                if not old.end_date:
                    old.end_date = today - timedelta(days=1)
                if not old.start_date:
                    # if old start missing, we leave it as-is (or set fallback if you want)
                    pass
                old.save(update_fields=["is_current", "end_date", "start_date"])

            new_sess, _ = AcademicSession.objects.get_or_create(session_name=target_session)
            new_sess.is_current = True
            if not new_sess.start_date:
                new_sess.start_date = today
            new_sess.end_date = None
            new_sess.save(update_fields=["is_current", "start_date", "end_date"])

        # 3) Clear drafts after success
        drafts.delete()

        if switch_session:
            messages.success(
                request,
                f"Promotion applied successfully ({applied_count} students). Active session moved to {target_session}."
            )
        else:
            messages.success(
                request,
                f"Promotion applied successfully ({applied_count} students). Session NOT changed (as per your choice)."
            )

        return redirect("promote_students")

    except Exception as e:
        messages.error(request, f"Promotion aborted due to error: {str(e)}")
        return redirect("promote_students")
def passout_students_view(request):
    perms = get_user_module_permissions(request.user, "passouts")
    if not perms.get("can_view"):
        messages.error(request, "Access Denied.")
        return redirect("dashboard")

    selected_session = request.GET.get('session', '').strip()
    search_query = request.GET.get('q', '').strip()

    available_sessions = list(
        StudentAlumni.objects.values_list('passed_session', flat=True).distinct().order_by('-passed_session')
    )
    if not selected_session and available_sessions:
        selected_session = available_sessions[0]

    alumni_records = StudentAlumni.objects.all().order_by('-passing_date')

    if selected_session:
        alumni_records = alumni_records.filter(passed_session=selected_session)

    if search_query:
        alumni_records = alumni_records.filter(
            Q(student_name__icontains=search_query) |
            Q(father_name__icontains=search_query) |
            Q(reg_no__icontains=search_query) |
            Q(passed_class__icontains=search_query)
        )

    total_dues = sum([a.remaining_dues for a in alumni_records])

    context = {
        'alumni_records': alumni_records,
        'available_sessions': available_sessions,
        'selected_session': selected_session,
        'search_query': search_query,
        'total_dues': total_dues,
    }
    return render(request, "passout_students.html", context)


# =========================================================================
# REVERT / UNLOCK PASSOUT STUDENT (Passout se wapis Active class mein lana)
# =========================================================================
@transaction.atomic
def revert_passout_student(request, alumni_id):
    perms = get_user_module_permissions(request.user, "passouts")
    if not perms.get("can_edit"):
        messages.error(request, "Access Denied.")
        return redirect("passout_students_view")

    if request.method == "POST":
        alumni = get_object_or_404(StudentAlumni, pk=alumni_id)
        student = alumni.student

        # Original class aur section jahan se passout hua tha
        orig_class = alumni.passed_class
        orig_section = alumni.passed_section

        # Uss class mein safe available roll number calculate karein
        new_roll = calculate_next_roll_no(orig_class, orig_section)

        # Student ko activate aur update karein
        student.student_class = orig_class
        student.section = orig_section
        student.roll_no = new_roll
        student.is_active = True
        student.save()

        student_name = alumni.student_name
        reg_no = alumni.reg_no

        # Alumni table se record remove karein
        alumni.delete()

        messages.success(
            request,
            f"Student {student_name} ({reg_no}) has been unlocked & restored to Class {orig_class} ({orig_section}) with Roll No #{new_roll}!"
        )
        return redirect('passout_students_view')

    return redirect('passout_students_view')
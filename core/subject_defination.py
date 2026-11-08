from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import connection
from django.contrib import messages
from core.models import SubjectDefination
from .user_rights import get_user_module_permissions


def subject_list(request):
    # ================= RIGHTS CHECK: VIEW =================
    perms = get_user_module_permissions(request.user, "subject_def")
    if not perms.get('can_view'):
        messages.error(request, "Access Denied: You do not have permission to view Subject Defination.")
        return redirect('dashboard')

    subjects = SubjectDefination.objects.values(
        'subject_name', 'subject_type', 'status', 'created_date'
    ).order_by('-created_date')

    subjects_list = list(subjects)
    total_subjects = len(subjects_list)
    theory_count = sum(1 for s in subjects_list if str(s.get('subject_type', '')).lower() == 'theory')
    practical_count = sum(1 for s in subjects_list if str(s.get('subject_type', '')).lower() == 'practical')

    context = {
        'subjects': subjects_list,
        'total_subjects': total_subjects,
        'theory_count': theory_count,
        'practical_count': practical_count,
        'perms': perms,
    }
    return render(request, 'subject_defination.html', context)


@require_POST
def add_subject(request):
    # ================= RIGHTS CHECK: CREATE =================
    perms = get_user_module_permissions(request.user, "subject_def")
    if not perms.get('can_add'):
        return JsonResponse({'status': 'error', 'message': 'Permission Denied: You cannot add subjects.'}, status=403)

    try:
        subject_name = (request.POST.get('subject_name') or '').strip()
        subject_type = (request.POST.get('subject_type') or '').strip()
        status = (request.POST.get('status') or 'Active').strip()

        if not subject_name or not subject_type:
            return JsonResponse({'status': 'error', 'message': 'All fields are required!'}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT subject_name FROM Subject_Defination WHERE subject_name = %s AND subject_type = %s",
                [subject_name, subject_type]
            )
            if cursor.fetchone():
                return JsonResponse({'status': 'error', 'message': 'This subject with the same type is already defined!'}, status=400)

            cursor.execute(
                """
                INSERT INTO Subject_Defination (subject_name, subject_type, status, created_date)
                VALUES (%s, %s, %s, %s)
                """,
                [subject_name, subject_type, status, timezone.now().date()]
            )

        return JsonResponse({'status': 'success', 'message': 'Subject added successfully!'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@require_POST
def edit_subject(request):
    # ================= RIGHTS CHECK: EDIT =================
    perms = get_user_module_permissions(request.user, "subject_def")
    if not perms.get('can_edit'):
        return JsonResponse({'status': 'error', 'message': 'Permission Denied: You cannot edit subjects.'}, status=403)

    try:
        old_name = (request.POST.get('old_subject_name') or '').strip()
        old_type = (request.POST.get('old_subject_type') or '').strip()
        subject_name = (request.POST.get('subject_name') or '').strip()
        subject_type = (request.POST.get('subject_type') or '').strip()
        status = (request.POST.get('status') or 'Active').strip()

        if not old_name or not old_type or not subject_name or not subject_type:
            return JsonResponse({'status': 'error', 'message': 'All fields are required!'}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT subject_name FROM Subject_Defination WHERE subject_name = %s AND subject_type = %s",
                [old_name, old_type]
            )
            if not cursor.fetchone():
                return JsonResponse({'status': 'error', 'message': 'Subject not found'}, status=404)

            if subject_name.lower() != old_name.lower() or subject_type.lower() != old_type.lower():
                cursor.execute(
                    "SELECT subject_name FROM Subject_Defination WHERE subject_name = %s AND subject_type = %s",
                    [subject_name, subject_type]
                )
                if cursor.fetchone():
                    return JsonResponse({'status': 'error', 'message': 'This subject with the same type is already defined!'}, status=400)

            cursor.execute(
                """
                UPDATE Subject_Defination
                SET subject_name = %s, subject_type = %s, status = %s
                WHERE subject_name = %s AND subject_type = %s
                """,
                [subject_name, subject_type, status, old_name, old_type]
            )

        return JsonResponse({'status': 'success', 'message': 'Subject updated successfully!'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@require_POST
def toggle_subject_status(request):
    # ================= RIGHTS CHECK: STATUS TOGGLE (EDIT) =================
    perms = get_user_module_permissions(request.user, "subject_def")
    if not perms.get('can_edit'):
        return JsonResponse({'status': 'error', 'message': 'Permission Denied.'}, status=403)

    try:
        name = (request.POST.get('subject_name') or '').strip()
        stype = (request.POST.get('subject_type') or '').strip()
        if not name or not stype:
            return JsonResponse({'status': 'error', 'message': 'Subject name/type missing'}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT status FROM Subject_Defination WHERE subject_name = %s AND subject_type = %s",
                [name, stype]
            )
            row = cursor.fetchone()
            if not row:
                return JsonResponse({'status': 'error', 'message': 'Subject not found'}, status=404)

            current = str(row[0] or '').strip()
            new_status = 'Inactive' if current.lower() == 'active' else 'Active'

            cursor.execute(
                "UPDATE Subject_Defination SET status = %s WHERE subject_name = %s AND subject_type = %s",
                [new_status, name, stype]
            )

        return JsonResponse({'status': 'success', 'new_status': new_status})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@require_POST
def delete_subject(request):
    # ================= RIGHTS CHECK: DELETE =================
    perms = get_user_module_permissions(request.user, "subject_def")
    if not perms.get('can_delete'):
        return JsonResponse({'status': 'error', 'message': 'Permission Denied: You cannot delete subjects.'}, status=403)

    try:
        name = (request.POST.get('subject_name') or '').strip()
        stype = (request.POST.get('subject_type') or '').strip()
        if not name or not stype:
            return JsonResponse({'status': 'error', 'message': 'Subject name/type missing'}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM Subject_Defination WHERE subject_name = %s AND subject_type = %s",
                [name, stype]
            )

        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
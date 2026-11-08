import re
import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages
from .models import CoreTeacher as Teacher, CoreStaffPayroll as Payroll
from .models import SubjectDefination
from django.contrib.auth.models import User
from .user_rights import get_user_module_permissions

def generate_teacher_id():
    """Auto-generates next teacher ID in TEC-1, TEC-2 format"""
    existing_ids = Teacher.objects.values_list('emp_id', flat=True)
    max_num = 0
    for emp_id in existing_ids:
        m = re.match(r'^TEC-(\d+)$', str(emp_id).strip(), re.IGNORECASE)
        if m:
            num = int(m.group(1))
            if num > max_num:
                max_num = num
    return f"TEC-{max_num + 1}"

def get_next_teacher_id_api(request):
    return JsonResponse({'next_emp_id': generate_teacher_id()})

def get_active_subjects():
    subjects = (
        SubjectDefination.objects
        .filter(status__iexact='Active')
        .values_list('subject_name', 'subject_type')
        .distinct()
        .order_by('subject_name', 'subject_type')
    )
    return [f"{name} ({stype})" for name, stype in subjects]

def teacher_list(request):
    # ================= RIGHTS CHECK: VIEW =================
    perms = get_user_module_permissions(request.user, "teachers")
    if not perms.get('can_view'):
        messages.error(request, "Access Denied: You do not have permission to view Teaching Faculty.")
        return redirect('dashboard')

    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    teachers = Teacher.objects.all().order_by('-id')

    if status_filter == 'active':
        teachers = teachers.filter(is_active=True)
    elif status_filter == 'inactive':
        teachers = teachers.filter(is_active=False)

    if search_query:
        teachers = teachers.filter(
            Q(name__icontains=search_query) | 
            Q(emp_id__icontains=search_query) |
            Q(subject__icontains=search_query) |
            Q(cnic__icontains=search_query) |
            Q(ref_name__icontains=search_query)
        )

    context = {
        "teachers": teachers,
        "search_query": search_query,
        "status_filter": status_filter,
        "next_teacher_id": generate_teacher_id(),
        "available_subjects": get_active_subjects(),
        "perms": perms,  # Injected into template
    }
    return render(request, "teachers.html", context)

def teacher_create(request):
    # ================= RIGHTS CHECK: CREATE =================
    perms = get_user_module_permissions(request.user, "teachers")
    if not perms.get('can_add'):
        messages.error(request, "Access Denied: You do not have permission to register teachers.")
        return redirect("teacher_list")

    if request.method == "POST":
        emp_id = request.POST.get('emp_id') or generate_teacher_id()
        salary_val = Decimal(request.POST.get('salary') or '0.00')
        password = request.POST.get('password', '').strip()

        teacher = Teacher(
            name=request.POST.get('name', '').strip(),
            emp_id=emp_id.strip(),
            cnic=request.POST.get('cnic') or None,
            subject=request.POST.get('subject'),
            qualification=request.POST.get('qualification') or None,
            salary=salary_val,
            dob=request.POST.get('dob') or None,
            joining_date=request.POST.get('joining_date') or None,
            gender=request.POST.get('gender') or None,
            marital_status=request.POST.get('marital_status') or None,
            relation_type=request.POST.get('relation_type') or None,
            relation_name=request.POST.get('relation_name', '').strip() or None,
            contact=request.POST.get('contact') or None,
            emergency_contact=request.POST.get('emergency_contact') or None,
            ref_name=request.POST.get('ref_name', '').strip() or None,
            ref_contact=request.POST.get('ref_contact', '').strip() or None,
            email=request.POST.get('email') or None,
            address=request.POST.get('address') or None,
            permanent_address=request.POST.get('permanent_address') or None,
            is_active=request.POST.get('is_active') == '1',
            password=password
        )

        if 'photo' in request.FILES:
            teacher.photo = request.FILES['photo']
        if 'cnic_photo' in request.FILES:
            teacher.cnic_photo = request.FILES['cnic_photo']

        teacher.save()

        if password and teacher.emp_id:
            user, _ = User.objects.get_or_create(username=teacher.emp_id)
            user.set_password(password)
            user.first_name = teacher.name
            user.is_active = teacher.is_active
            user.save()

        messages.success(request, f'Teacher "{teacher.name}" registered with ID: {emp_id}!')
    return redirect("teacher_list")

def teacher_update(request, pk):
    # ================= RIGHTS CHECK: EDIT =================
    perms = get_user_module_permissions(request.user, "teachers")
    if not perms.get('can_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit teacher profiles.")
        return redirect("teacher_list")

    teacher = get_object_or_404(Teacher, pk=pk)
    if request.method == "POST":
        new_salary = Decimal(request.POST.get('salary') or '0.00')
        teacher.name = request.POST.get('name', '').strip()
        teacher.emp_id = request.POST.get('emp_id', '').strip()
        teacher.cnic = request.POST.get('cnic') or None
        teacher.subject = request.POST.get('subject')
        teacher.qualification = request.POST.get('qualification') or None
        teacher.salary = new_salary
        teacher.dob = request.POST.get('dob') or None
        teacher.joining_date = request.POST.get('joining_date') or None
        teacher.gender = request.POST.get('gender') or None
        teacher.marital_status = request.POST.get('marital_status') or None
        teacher.relation_type = request.POST.get('relation_type') or None
        teacher.relation_name = request.POST.get('relation_name', '').strip() or None
        teacher.contact = request.POST.get('contact') or None
        teacher.emergency_contact = request.POST.get('emergency_contact') or None
        teacher.ref_name = request.POST.get('ref_name', '').strip() or None
        teacher.ref_contact = request.POST.get('ref_contact', '').strip() or None
        teacher.email = request.POST.get('email') or None
        teacher.address = request.POST.get('address') or None
        teacher.permanent_address = request.POST.get('permanent_address') or None
        teacher.is_active = request.POST.get('is_active') == '1'

        new_password = request.POST.get('password', '').strip()
        if new_password:
            teacher.password = new_password
            if teacher.emp_id:
                user, _ = User.objects.get_or_create(username=teacher.emp_id)
                user.set_password(new_password)
                user.first_name = teacher.name
                user.is_active = teacher.is_active
                user.save()
        else:
            if teacher.emp_id:
                user = User.objects.filter(username=teacher.emp_id).first()
                if user:
                    user.first_name = teacher.name
                    user.is_active = teacher.is_active
                    user.save()

        if 'photo' in request.FILES:
            teacher.photo = request.FILES['photo']
        if 'cnic_photo' in request.FILES:
            teacher.cnic_photo = request.FILES['cnic_photo']

        teacher.save()

        current_date = datetime.date.today()
        pending_payrolls = Payroll.objects.filter(
            teacher=teacher,
            status='Pending',
            payroll_month=current_date.month,
            payroll_year=current_date.year
        )
        for p in pending_payrolls:
            p.basic_salary = new_salary
            p.net_salary = max(Decimal('0.00'), new_salary + p.extra_allowance - p.deduction)
            p.save()

        messages.success(request, f'Teacher "{teacher.name}" updated successfully!')
    return redirect("teacher_list")

def teacher_toggle_status(request, pk):
    perms = get_user_module_permissions(request.user, "teachers")
    if not perms.get('can_edit'):
        messages.error(request, "Access Denied: You do not have permission to change teacher status.")
        return redirect("teacher_list")

    teacher = get_object_or_404(Teacher, pk=pk)
    teacher.is_active = not teacher.is_active
    teacher.save()
    status_str = "Active" if teacher.is_active else "Deactivated"
    messages.success(request, f'Teacher "{teacher.name}" is now {status_str}.')
    return redirect("teacher_list")

def teacher_delete(request, pk):
    # ================= RIGHTS CHECK: DELETE =================
    perms = get_user_module_permissions(request.user, "teachers")
    if not perms.get('can_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete teachers.")
        return redirect("teacher_list")

    teacher = get_object_or_404(Teacher, pk=pk)
    if request.method == "POST":
        name = teacher.name
        teacher.delete()
        messages.success(request, f'Teacher "{name}" removed successfully!')
    return redirect("teacher_list")
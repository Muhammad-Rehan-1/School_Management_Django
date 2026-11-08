import re
import json
import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages
from django.db import connection
from .models import CoreStaff as Staff, CoreStaffPayroll as Payroll
from django.contrib.auth.models import User
from .user_rights import get_user_module_permissions

def get_all_staff_roles():
    """Database se all active staff roles aur unke prefix fetch karta hai"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT role_name, prefix FROM dbo.core_staff_role ORDER BY role_name")
        return cursor.fetchall()

def get_role_prefix(role_name):
    with connection.cursor() as cursor:
        cursor.execute("SELECT prefix FROM dbo.core_staff_role WHERE role_name = %s", [role_name])
        row = cursor.fetchone()
        if row and row[0]:
            return row[0].strip().upper()
    cleaned = re.sub(r'[^A-Za-z]', '', role_name or 'STF')
    return (cleaned[:3] or 'STF').upper()

def generate_staff_id(role):
    prefix = get_role_prefix(role)
    existing_ids = Staff.objects.values_list('emp_id', flat=True)
    
    max_num = 0
    pattern = rf'^{prefix}-(\d+)$'
    for emp_id in existing_ids:
        m = re.match(pattern, str(emp_id).strip(), re.IGNORECASE)
        if m:
            num = int(m.group(1))
            if num > max_num:
                max_num = num
    return f"{prefix}-{max_num + 1}"

def get_next_staff_id_api(request):
    role = request.GET.get('role', '').strip()
    next_id = generate_staff_id(role) if role else "STF-1"
    return JsonResponse({'next_emp_id': next_id})

def add_staff_role_api(request):
    perms = get_user_module_permissions(request.user, "staff")
    if not perms.get('can_add'):
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            role_name = data.get('role_name', '').strip()
            prefix = data.get('prefix', '').strip().upper()

            if not role_name:
                return JsonResponse({'success': False, 'message': 'Role name is required.'}, status=400)

            if not prefix:
                cleaned = re.sub(r'[^A-Za-z]', '', role_name)
                prefix = (cleaned[:3] or 'STF').upper()

            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM dbo.core_staff_role WHERE LOWER(role_name) = LOWER(%s)", [role_name])
                if cursor.fetchone()[0] > 0:
                    return JsonResponse({'success': False, 'message': 'This role already exists.'}, status=400)

                cursor.execute("INSERT INTO dbo.core_staff_role (role_name, prefix) VALUES (%s, %s)", [role_name, prefix])

            return JsonResponse({'success': True, 'role_name': role_name, 'prefix': prefix})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

def staff_list(request):
    # ================= RIGHTS CHECK: VIEW =================
    perms = get_user_module_permissions(request.user, "staff")
    if not perms.get('can_view'):
        messages.error(request, "Access Denied: You do not have permission to view Administrative Staff.")
        return redirect('dashboard')

    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    staff_members = Staff.objects.all().order_by('-id')

    if status_filter == 'active':
        staff_members = staff_members.filter(is_active=True)
    elif status_filter == 'inactive':
        staff_members = staff_members.filter(is_active=False)

    if search_query:
        staff_members = staff_members.filter(
            Q(name__icontains=search_query) | 
            Q(emp_id__icontains=search_query) |
            Q(role__icontains=search_query) |
            Q(cnic__icontains=search_query) |
            Q(ref_name__icontains=search_query)
        )

    roles_data = get_all_staff_roles()
    available_roles = [{'name': r[0], 'prefix': r[1]} for r in roles_data]

    context = {
        "staff_members": staff_members,
        "search_query": search_query,
        "status_filter": status_filter,
        "available_roles": available_roles,
        "perms": perms,  # Injected into template
    }
    return render(request, "staff.html", context)

def staff_create(request):
    # ================= RIGHTS CHECK: CREATE =================
    perms = get_user_module_permissions(request.user, "staff")
    if not perms.get('can_add'):
        messages.error(request, "Access Denied: You do not have permission to register staff.")
        return redirect("staff_list")

    if request.method == "POST":
        role = request.POST.get('role', '').strip() or 'Other'
        emp_id = request.POST.get('emp_id', '').strip() or generate_staff_id(role)
        salary_val = Decimal(request.POST.get('salary') or '0.00')
        password = request.POST.get('password', '').strip()

        staff = Staff()
        staff.name = request.POST.get('name', '').strip()
        staff.emp_id = emp_id
        staff.cnic = request.POST.get('cnic', '').strip() or None
        staff.role = role
        staff.qualification = request.POST.get('qualification', '').strip() or None
        staff.salary = salary_val
        staff.dob = request.POST.get('dob') or None
        staff.joining_date = request.POST.get('joining_date') or None
        staff.gender = request.POST.get('gender') or None
        staff.marital_status = request.POST.get('marital_status') or None
        staff.relation_type = request.POST.get('relation_type') or None
        staff.relation_name = request.POST.get('relation_name', '').strip() or None
        staff.contact = request.POST.get('contact', '').strip() or None
        staff.emergency_contact = request.POST.get('emergency_contact', '').strip() or None
        staff.ref_name = request.POST.get('ref_name', '').strip() or None
        staff.ref_contact = request.POST.get('ref_contact', '').strip() or None
        staff.email = request.POST.get('email', '').strip() or None
        staff.address = request.POST.get('address', '').strip() or None
        staff.permanent_address = request.POST.get('permanent_address', '').strip() or None
        staff.is_active = request.POST.get('is_active') == '1'
        staff.password = password

        if 'photo' in request.FILES:
            staff.photo = request.FILES['photo']
        if 'cnic_photo' in request.FILES:
            staff.cnic_photo = request.FILES['cnic_photo']

        staff.save()

        if password and staff.emp_id:
            user, _ = User.objects.get_or_create(username=staff.emp_id)
            user.set_password(password)
            user.first_name = staff.name
            user.is_active = staff.is_active
            user.save()

        messages.success(request, f'Employee "{staff.name}" registered with ID: {emp_id}!')
        return redirect("staff_list")
    return redirect("staff_list")

def staff_update(request, pk):
    # ================= RIGHTS CHECK: EDIT =================
    perms = get_user_module_permissions(request.user, "staff")
    if not perms.get('can_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit staff profiles.")
        return redirect("staff_list")

    staff = get_object_or_404(Staff, pk=pk)
    if request.method == "POST":
        new_salary = Decimal(request.POST.get('salary') or '0.00')
        staff.name = request.POST.get('name', '').strip()
        staff.emp_id = request.POST.get('emp_id', '').strip()
        staff.cnic = request.POST.get('cnic', '').strip() or None
        staff.role = request.POST.get('role', '').strip()
        staff.qualification = request.POST.get('qualification', '').strip() or None
        staff.salary = new_salary
        staff.dob = request.POST.get('dob') or None
        staff.joining_date = request.POST.get('joining_date') or None
        staff.gender = request.POST.get('gender') or None
        staff.marital_status = request.POST.get('marital_status') or None
        staff.relation_type = request.POST.get('relation_type') or None
        staff.relation_name = request.POST.get('relation_name', '').strip() or None
        staff.contact = request.POST.get('contact', '').strip() or None
        staff.emergency_contact = request.POST.get('emergency_contact', '').strip() or None
        staff.ref_name = request.POST.get('ref_name', '').strip() or None
        staff.ref_contact = request.POST.get('ref_contact', '').strip() or None
        staff.email = request.POST.get('email', '').strip() or None
        staff.address = request.POST.get('address', '').strip() or None
        staff.permanent_address = request.POST.get('permanent_address', '').strip() or None
        staff.is_active = request.POST.get('is_active') == '1'

        new_password = request.POST.get('password', '').strip()
        if new_password:
            staff.password = new_password
            if staff.emp_id:
                user, _ = User.objects.get_or_create(username=staff.emp_id)
                user.set_password(new_password)
                user.first_name = staff.name
                user.is_active = staff.is_active
                user.save()
        else:
            if staff.emp_id:
                user = User.objects.filter(username=staff.emp_id).first()
                if user:
                    user.first_name = staff.name
                    user.is_active = staff.is_active
                    user.save()

        if 'photo' in request.FILES:
            staff.photo = request.FILES['photo']
        if 'cnic_photo' in request.FILES:
            staff.cnic_photo = request.FILES['cnic_photo']

        staff.save()

        try:
            current_date = datetime.date.today()
            pending_payrolls = Payroll.objects.filter(
                staff=staff,
                status='Pending',
                payroll_month=current_date.month,
                payroll_year=current_date.year
            )
            for p in pending_payrolls:
                p.basic_salary = new_salary
                p.net_salary = max(Decimal('0.00'), new_salary + p.extra_allowance - p.deduction)
                p.save()
        except Exception:
            pass

        messages.success(request, f'Employee "{staff.name}" updated successfully!')
        return redirect("staff_list")
    return redirect("staff_list")

def staff_toggle_status(request, pk):
    perms = get_user_module_permissions(request.user, "staff")
    if not perms.get('can_edit'):
        messages.error(request, "Access Denied: You do not have permission to change employee status.")
        return redirect("staff_list")

    staff = get_object_or_404(Staff, pk=pk)
    staff.is_active = not staff.is_active
    staff.save()
    status_str = "Active" if staff.is_active else "Deactivated"
    messages.success(request, f'Employee "{staff.name}" is now {status_str}.')
    return redirect("staff_list")

def staff_delete(request, pk):
    # ================= RIGHTS CHECK: DELETE =================
    perms = get_user_module_permissions(request.user, "staff")
    if not perms.get('can_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete staff records.")
        return redirect("staff_list")

    staff = get_object_or_404(Staff, pk=pk)
    if request.method == "POST":
        name = staff.name
        if staff.emp_id:
            User.objects.filter(username=staff.emp_id).delete()
        staff.delete()
        messages.success(request, f'Employee "{name}" deleted successfully!')
    return redirect("staff_list")
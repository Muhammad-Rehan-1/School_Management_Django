from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import connection
import re
# Aapke actual models import ho gaye
from .models import CoreStudent as Student, ClassDefination, StudentAlumni
from .user_rights import get_user_module_permissions


def get_active_classes():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT [class] 
            FROM Class_defination 
            WHERE status = 'Active' 
            ORDER BY [class]
        """)
        return [row[0] for row in cursor.fetchall()]


def generate_next_reg_no():
    students = Student.objects.filter(reg_no__startswith='REG-')
    max_num = 0
    for s in students:
        val = str(s.reg_no or '').replace('REG-', '').strip()
        if val.isdigit():
            max_num = max(max_num, int(val))
    return f"REG-{str(max_num + 1).zfill(4)}"


def get_passout_sessions():
    """
    StudentAlumni table se distinct passed_sessions fetch karta hai
    """
    sessions = list(
        StudentAlumni.objects.exclude(passed_session__isnull=True)
        .exclude(passed_session='')
        .values_list('passed_session', flat=True)
        .distinct()
    )
    if not sessions:
        sessions = ['2026-2027']
    return sorted(list(set(sessions)), reverse=True)


def student_list(request):
    # ================= RIGHTS CHECK: VIEW ACCESS =================
    perms = get_user_module_permissions(request.user, "students")
    if not perms.get('can_view'):
        messages.error(request, "Access Denied: You do not have permission to view the Students Directory.")
        fallback = 'teacher_dashboard' if request.session.get('user_role') == 'Teacher' else 'dashboard'
        return redirect(request.META.get('HTTP_REFERER') or fallback)

    selected_class = request.GET.get('class', '').strip()
    selected_section = request.GET.get('section', '').strip()
    status_filter = request.GET.get('status', '').strip()
    passout_filter = request.GET.get('passout_session', '').strip()
    search_query = request.GET.get('q', '').strip()

    passout_sessions_list = get_passout_sessions()

    # =========================================================================
    # CASE 1: JAB PASSOUT / ALUMNI FILTER CHOOSE KIYA GAYA HO
    # =========================================================================
    if passout_filter:
        alumni_qs = StudentAlumni.objects.select_related('student').all().order_by('-id')

        # Session filter (e.g. '2026-2027' ya 'all_passout')
        if passout_filter != 'all_passout':
            alumni_qs = alumni_qs.filter(passed_session__iexact=passout_filter)

        # Class filter
        if selected_class:
            alumni_qs = alumni_qs.filter(passed_class__iexact=selected_class)

        # Section filter
        if selected_section:
            alumni_qs = alumni_qs.filter(
                Q(passed_section__iexact=selected_section) |
                Q(passed_section__icontains=selected_section)
            )

        # Search Query
        if search_query:
            alumni_qs = alumni_qs.filter(
                Q(student_name__icontains=search_query) |
                Q(father_name__icontains=search_query) |
                Q(reg_no__icontains=search_query) |
                Q(student__roll_no__icontains=search_query)
            )

        students = []
        for alm in alumni_qs:
            if alm.student:
                st = alm.student
                st.passout_session_info = alm.passed_session
                st.is_passout_record = True
                st.student_class = alm.passed_class
                st.section = alm.passed_section
                st.remaining_dues = alm.remaining_dues
                students.append(st)
            else:
                class MockStudent:
                    pass
                m = MockStudent()
                m.id = alm.id
                m.name = alm.student_name
                m.father_name = alm.father_name
                m.mother_name = ''
                m.father_cnic = ''
                m.reg_no = alm.reg_no
                m.student_class = alm.passed_class
                m.section = alm.passed_section
                m.roll_no = '—'
                m.monthly_fee = alm.remaining_dues
                m.admission_fee = Decimal('0.00')
                m.transport_charges = Decimal('0.00')
                m.other_charges = Decimal('0.00')
                m.fee_concession = Decimal('0.00')
                m.is_active = False
                m.is_passout_record = True
                m.dob = None
                m.enrolment_date = None
                m.gender = ''
                m.contact = ''
                m.address = ''
                m.permanent_address = ''
                m.photo = None
                m.form_b_image = None
                m.password = ''
                m.passout_session_info = alm.passed_session
                students.append(m)

    # =========================================================================
    # CASE 2: DEFAULT (ALL ACTIVE & INACTIVE STUDENTS DIRECTORY)
    # =========================================================================
    else:
        students_qs = Student.objects.all().order_by('-id')
        alumni_map = dict(StudentAlumni.objects.values_list('reg_no', 'passed_session'))

        if selected_class:
            students_qs = students_qs.filter(student_class__iexact=selected_class)
        if selected_section:
            students_qs = students_qs.filter(
                Q(section__iexact=selected_section) |
                Q(section__iexact=f"Section {selected_section}") |
                Q(section__icontains=selected_section)
            )
        if status_filter == 'active':
            students_qs = students_qs.filter(is_active=True)
        elif status_filter == 'inactive':
            students_qs = students_qs.filter(is_active=False)

        if search_query:
            students_qs = students_qs.filter(
                Q(name__icontains=search_query) |
                Q(father_name__icontains=search_query) |
                Q(reg_no__icontains=search_query) |
                Q(roll_no__icontains=search_query) |
                Q(section__icontains=search_query) |
                Q(father_cnic__icontains=search_query)
            )

        students = list(students_qs)
        for st in students:
            st.passout_session_info = alumni_map.get(st.reg_no, None)
            st.is_passout_record = bool(st.passout_session_info)

    available_sections = []
    if selected_class:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT RTRIM(LTRIM(section)) 
                FROM Class_defination 
                WHERE [class] = %s AND status = 'Active' 
                ORDER BY RTRIM(LTRIM(section))
            """, [selected_class])
            available_sections = [row[0] for row in cursor.fetchall() if row[0]]

    context = {
        'students': students,
        'selected_class': selected_class,
        'selected_section': selected_section,
        'status_filter': status_filter,
        'passout_filter': passout_filter,
        'passout_sessions': passout_sessions_list,
        'search_query': search_query,
        'available_classes': get_active_classes(),
        'available_sections': available_sections,
        'next_reg_no': generate_next_reg_no(),
        'perms': perms,  # Template access rights context mein pass kar diye gaye hain
    }
    return render(request, "students.html", context)


def student_create(request):
    # ================= RIGHTS CHECK: CREATE ACCESS =================
    perms = get_user_module_permissions(request.user, "students")
    if not perms.get('can_add'):
        messages.error(request, "Access Denied: You do not have permission to register new students.")
        return redirect('student_list')

    if request.method == "POST":
        actual_fee = Decimal(request.POST.get('actual_fee') or request.POST.get('monthly_fee') or '0.00')
        concession = Decimal(request.POST.get('fee_concession') or '0.00')
        net_monthly_fee = max(Decimal('0.00'), actual_fee - concession)

        reg_no = request.POST.get('reg_no', '').strip() or generate_next_reg_no()
        roll_no = request.POST.get('roll_no', '').strip()

        student = Student()
        try:
            student.contact = _validate_phone(request.POST.get('contact', ''))
            student.father_cnic = _validate_cnic(request.POST.get('father_cnic', ''))

            exp_days = int(request.POST.get('challan_expiry_days') or 8)
            exp_days = max(1, min(exp_days, 60))  # 1-60 clamp
            student.challan_expiry_days = exp_days
        except ValueError as ve:
            messages.error(request, str(ve))
            return redirect('student_list')
        
        student.reg_no = reg_no
        student.roll_no = roll_no
        student.name = request.POST.get('name', '').strip()
        student.father_name = request.POST.get('father_name', '').strip()
        student.mother_name = request.POST.get('mother_name', '').strip() or None
        student.father_cnic = request.POST.get('father_cnic', '').strip() or None
        student.student_class = request.POST.get('student_class', '').strip()
        student.section = request.POST.get('section', '').strip() or None
        student.previous_school = request.POST.get('previous_school', '').strip() or None
        student.dob = request.POST.get('dob') or None
        student.enrolment_date = request.POST.get('enrolment_date') or None
        student.gender = request.POST.get('gender') or None
        student.is_active = request.POST.get('is_active') == '1'
        student.contact = request.POST.get('contact', '').strip() or None
        student.address = request.POST.get('address', '').strip() or None
        student.permanent_address = request.POST.get('permanent_address', '').strip() or None

        student.admission_fee = Decimal(request.POST.get('admission_fee') or '0.00')
        student.monthly_fee = net_monthly_fee
        student.transport_charges = Decimal(request.POST.get('transport_charges') or '0.00')
        student.other_charges = Decimal(request.POST.get('other_charges') or '0.00')

        password = request.POST.get('password', '').strip()
        student.password = password

        if 'photo' in request.FILES:
            student.photo = request.FILES['photo']
        if 'form_b_image' in request.FILES:
            student.form_b_image = request.FILES['form_b_image']

        student.save()

        login_id = student.reg_no or student.roll_no
        if password and login_id:
            user, created = User.objects.get_or_create(username=login_id)
            user.set_password(password)
            user.first_name = student.name
            user.is_active = student.is_active
            user.save()

        messages.success(request, f'Student "{student.name}" registered with Reg No: {student.reg_no}!')
        return redirect('student_list')
    return redirect('student_list')


def student_update(request, pk):
    # ================= RIGHTS CHECK: EDIT ACCESS =================
    perms = get_user_module_permissions(request.user, "students")
    if not perms.get('can_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit student profiles.")
        return redirect('student_list')

    student = get_object_or_404(Student, pk=pk)
    if request.method == "POST":
        try:
            student.contact = _validate_phone(request.POST.get('contact', ''))
            student.father_cnic = _validate_cnic(request.POST.get('father_cnic', ''))

            exp_days = int(request.POST.get('challan_expiry_days') or (student.challan_expiry_days or 8))
            exp_days = max(1, min(exp_days, 60))
            student.challan_expiry_days = exp_days
        except ValueError as ve:
            messages.error(request, str(ve))
            return redirect('student_list')
        
        actual_fee = Decimal(request.POST.get('actual_fee') or request.POST.get('monthly_fee') or '0.00')
        concession = Decimal(request.POST.get('fee_concession') or '0.00')
        net_monthly_fee = max(Decimal('0.00'), actual_fee - concession)

        student.name = request.POST.get('name', '').strip()
        student.father_name = request.POST.get('father_name', '').strip()
        student.mother_name = request.POST.get('mother_name', '').strip() or None
        student.father_cnic = request.POST.get('father_cnic', '').strip() or None
        student.student_class = request.POST.get('student_class', '').strip()
        student.section = request.POST.get('section', '').strip() or None
        student.roll_no = request.POST.get('roll_no', '').strip()
        student.previous_school = request.POST.get('previous_school', '').strip() or None
        student.dob = request.POST.get('dob') or None
        student.enrolment_date = request.POST.get('enrolment_date') or None
        student.gender = request.POST.get('gender') or None
        student.is_active = request.POST.get('is_active') == '1'
        student.contact = request.POST.get('contact', '').strip() or None
        student.address = request.POST.get('address', '').strip() or None
        student.permanent_address = request.POST.get('permanent_address', '').strip() or None

        student.admission_fee = Decimal(request.POST.get('admission_fee') or '0.00')
        student.monthly_fee = net_monthly_fee
        student.transport_charges = Decimal(request.POST.get('transport_charges') or '0.00')
        student.other_charges = Decimal(request.POST.get('other_charges') or '0.00')

        new_password = request.POST.get('password', '').strip()
        login_id = student.reg_no or student.roll_no

        if new_password:
            student.password = new_password
            if login_id:
                user, _ = User.objects.get_or_create(username=login_id)
                user.set_password(new_password)
                user.first_name = student.name
                user.is_active = student.is_active
                user.save()
        else:
            if login_id:
                user = User.objects.filter(username=login_id).first()
                if user:
                    user.first_name = student.name
                    user.is_active = student.is_active
                    user.save()

        if 'photo' in request.FILES:
            student.photo = request.FILES['photo']
        if 'form_b_image' in request.FILES:
            student.form_b_image = request.FILES['form_b_image']

        student.save()
        messages.success(request, f'Student "{student.name}" updated successfully!')
        return redirect('student_list')
    return redirect('student_list')


def student_toggle_status(request, pk):
    # ================= RIGHTS CHECK: STATUS TOGGLE (EDIT) ACCESS =================
    perms = get_user_module_permissions(request.user, "students")
    if not perms.get('can_edit'):
        messages.error(request, "Access Denied: You do not have permission to change student status.")
        return redirect('student_list')

    student = get_object_or_404(Student, pk=pk)
    student.is_active = not student.is_active
    student.save()
    status_text = "activated" if student.is_active else "deactivated"
    messages.success(request, f'Student "{student.name}" has been {status_text}.')
    return redirect('student_list')


def student_delete(request, pk):
    # ================= RIGHTS CHECK: DELETE ACCESS =================
    perms = get_user_module_permissions(request.user, "students")
    if not perms.get('can_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete student records.")
        return redirect('student_list')

    student = get_object_or_404(Student, pk=pk)
    if request.method == "POST":
        name = student.name
        login_id = student.reg_no or student.roll_no
        if login_id:
            User.objects.filter(username=login_id).delete()
        student.delete()
        messages.success(request, f'Student "{name}" removed successfully!')
    return redirect('student_list')


def get_class_sections_api(request):
    class_name = request.GET.get('class', '').strip()
    if not class_name:
        return JsonResponse({'sections': []})

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT section 
            FROM Class_defination 
            WHERE [class] = %s AND status = 'Active' 
            ORDER BY section
        """, [class_name])
        sections = [row[0] for row in cursor.fetchall()]

    return JsonResponse({'sections': sections})


def get_next_reg_no_api(request):
    return JsonResponse({'next_reg_no': generate_next_reg_no()})


def get_next_roll_no_api(request):
    class_name = request.GET.get('class', '').strip()
    section_name = request.GET.get('section', '').strip()

    if not class_name or not section_name:
        return JsonResponse({'next_roll_no': ''})

    existing_students = Student.objects.filter(student_class__iexact=class_name, section__iexact=section_name)
    max_num = 0
    prefix = f"{class_name}-{section_name}-"
    
    for s in existing_students:
        r = str(s.roll_no or '').replace(prefix, "").strip()
        if r.isdigit():
            max_num = max(max_num, int(r))

    next_roll_no = f"{prefix}{max_num + 1}"
    return JsonResponse({'next_roll_no': next_roll_no})


PHONE_RE = re.compile(r"^03\d{2} \d{7}$")          # 0300 1234567
CNIC_RE  = re.compile(r"^\d{5}-\d{7}-\d{1}$")      # 34602-7704453-0

def _validate_phone(phone: str) -> str:
    phone = (phone or "").strip()
    if phone and not PHONE_RE.match(phone):
        raise ValueError("Contact number format invalid. Use: 0300 0000000")
    return phone

def _validate_cnic(cnic: str) -> str:
    cnic = (cnic or "").strip()
    if cnic and not CNIC_RE.match(cnic):
        raise ValueError("CNIC format invalid. Use: 34602-7704453-0")
    return cnic
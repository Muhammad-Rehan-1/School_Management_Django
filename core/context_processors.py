import logging
from .models import SchoolProfile
from .models import *
from .user_rights import get_user_module_permissions

from django.db.models import Q 

logger = logging.getLogger(__name__)

FIELDS = ['school_name', 'campus_name', 'registration_no',
          'board_affiliation', 'address', 'phone_number', 'email']

DEFAULT_SCHOOL = {f: '' for f in FIELDS}
DEFAULT_SCHOOL['school_name'] = 'School'


def get_school_profile():
    """Python code (ReportLab PDFs, challan, slips) mein yeh call karo."""
    data = dict(DEFAULT_SCHOOL)
    try:
        row = (SchoolProfile.objects
               .filter(is_active=True)
               .order_by('-id')
               .values(*FIELDS)
               .first())
        if row:
            data.update({k: (v or '') for k, v in row.items()})
    except Exception:
        logger.exception("SchoolProfile load nahi hua")
    return data


def school_profile(request):
    """Templates ke liye — settings.py mein registered hai."""
    return {'school': get_school_profile()}

def current_user_context(request):
    """
    Har template ko logged-in user ka profile object, name, role aur avatar provide karta hai.
    """
    if not request.user.is_authenticated:
        return {
            'logged_user_name': 'Guest',
            'logged_user_role': 'Visitor',
            'logged_user_photo': None,
            'logged_user_initial': 'G'
        }

    user = request.user
    username = user.username.strip()
    photo_url = None
    role = "Staff"
    display_name = user.get_full_name() or user.username

    # -------------------------------------------------------------
    # 1. PEHLE CHECK KAREIN: KYA YEH STUDENT HAI? (Roll No ya Reg No)
    # -------------------------------------------------------------
    student = CoreStudent.objects.filter(
        Q(roll_no__iexact=username) | Q(reg_no__iexact=username),
        is_active=True
    ).first()

    if student:
        display_name = student.name
        # Class ke sath proper Student role
        role = f"Student ({student.student_class})" if student.student_class else "Student"
        if student.photo:
            try:
                photo_url = student.photo.url
            except Exception:
                photo_url = None

    # -------------------------------------------------------------
    # 2. DOOSRA CHECK: KYA YEH TEACHER HAI? (Emp ID)
    # -------------------------------------------------------------
    elif CoreTeacher.objects.filter(emp_id__iexact=username, is_active=True).exists():
        teacher = CoreTeacher.objects.filter(emp_id__iexact=username, is_active=True).first()
        display_name = teacher.name
        role = f"Teacher ({teacher.subject})" if teacher.subject else "Teacher"
        if teacher.photo:
            try:
                photo_url = teacher.photo.url
            except Exception:
                photo_url = None

    # -------------------------------------------------------------
    # 3. TEESRA CHECK: KYA YEH STAFF MEMBER HAI? (Emp ID)
    # -------------------------------------------------------------
    elif CoreStaff.objects.filter(emp_id__iexact=username, is_active=True).exists():
        staff = CoreStaff.objects.filter(emp_id__iexact=username, is_active=True).first()
        display_name = staff.name
        role = staff.role if staff.role else "Staff"
        if staff.photo:
            try:
                photo_url = staff.photo.url
            except Exception:
                photo_url = None

    # -------------------------------------------------------------
    # 4. SUPERADMIN CHECK
    # -------------------------------------------------------------
    elif user.is_superuser:
        display_name = user.first_name or "Admin"
        role = "Super Admin"

    initial = display_name[0].upper() if display_name else 'U'

    return {
        'logged_user_name': display_name.title(),
        'logged_user_role': role,
        'logged_user_photo': photo_url,
        'logged_user_initial': initial
    }

import datetime
from .models import AcademicSession

def academic_session_processor(request):
    curr_sess = AcademicSession.objects.filter(is_current=True).order_by('-id').first()

    if curr_sess and curr_sess.session_name:
        academic_year = curr_sess.session_name
    else:
        # dynamic fallback (no hardcode)
        y = datetime.date.today().year
        academic_year = f"{y}-{y+1}"

    # years list for dropdown (optional but useful)
    session_years = []
    if curr_sess and curr_sess.start_date and curr_sess.end_date:
        session_years = list(range(curr_sess.start_date.year, curr_sess.end_date.year + 1))
    else:
        # parse "2026-2027" style
        try:
            a, b = academic_year.split('-')
            session_years = list(range(int(a), int(b) + 1))
        except Exception:
            y = datetime.date.today().year
            session_years = [y - 1, y, y + 1]

    return {
        'active_academic_year': academic_year,
        'active_session': curr_sess,
        'session_years': session_years,     # dropdown helper
    }




def user_permissions_processor(request):
    """
    Har template aur sidebar navigation ke liye module permissions inject karta hai.
    """
    if not request.user.is_authenticated:
        return {'nav_perms': {}}

    user = request.user
    
    # Tamam main modules ki access evaluate karein
    modules = [
    'dashboard', 'class_def', 'subject_def', 'students',
    'teachers', 'staff',
    'fee_records', 'add_fees', 'extra_fee', 'payroll',
    'attendance', 'staff_attendance',
    'timetable', 'exam', 'results', 'promote', 'passouts',
    'transport', 'notice', 'reports', 'user_rights'
]

    perms_dict = {}
    for mod in modules:
        perms_dict[mod] = get_user_module_permissions(user, mod)

    return {
        'nav_perms': perms_dict,
    }
from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect

from .models import (
    CoreTeacher,
    CoreStudent,
    TimetableSlot,
    TimetablePeriod,
    TimetableDay,
    StaffAttendance,
    AttendanceLock,
    CoreExam,
    CoreStaffPayroll,
    Notice,
    AcademicSession,
    SchoolProfile,
)
from .user_rights import get_user_module_permissions


# =========================================================
# HELPERS
# =========================================================

def get_teacher_from_request(request):
    """Teacher ko session teacher_id ya username (emp_id) se dhoondta hai."""
    teacher_id = request.session.get("teacher_id")
    if teacher_id:
        teacher = CoreTeacher.objects.filter(id=teacher_id, is_active=True).first()
        if teacher:
            return teacher

    username = getattr(request.user, "username", "")
    if username:
        teacher = CoreTeacher.objects.filter(emp_id__iexact=username, is_active=True).first()
        if teacher:
            return teacher

    return None


def get_active_session():
    try:
        current = AcademicSession.objects.filter(is_current=True).first()
        if current:
            return current.session_name

        latest = AcademicSession.objects.order_by("-start_date", "-id").first()
        if latest:
            return latest.session_name
    except Exception as exc:
        print("Teacher Dashboard - Academic session error:", exc)

    return ""


def get_today_timetable_day():
    today_name = date.today().strftime("%A")
    return TimetableDay.objects.filter(name__iexact=today_name).first()


def get_student_queryset(cls, section):
    cls = (cls or "").strip()
    section = (section or "").strip()

    if not cls:
        return CoreStudent.objects.none()

    qs = CoreStudent.objects.filter(student_class__iexact=cls, is_active=True)
    if section:
        exact = qs.filter(section__iexact=section)
        if exact.exists():
            return exact
        if section.upper() == "A":
            blank = qs.filter(Q(section__isnull=True) | Q(section=""))
            if blank.exists():
                return blank
        return CoreStudent.objects.none()

    return qs


# =========================================================
# TEACHER DASHBOARD VIEW
# =========================================================

@login_required(login_url="login")
def teacher_dashboard_view(request):
    teacher = get_teacher_from_request(request)

    # Superuser testing fallback
    if not teacher and request.user.is_superuser:
        teacher = CoreTeacher.objects.filter(is_active=True).first()

    if not teacher:
        messages.error(request, "Teacher profile could not be found for this login.")
        return redirect("dashboard")

    today = date.today()
    current_time = datetime.now().time()
    school = SchoolProfile.objects.filter(is_active=True).first()
    active_session = get_active_session()

    # ================= RIGHTS EVALUATION =================
    perms_att = get_user_module_permissions(request.user, "attendance")
    perms_exam = get_user_module_permissions(request.user, "exam")
    perms_tt = get_user_module_permissions(request.user, "timetable")
    perms_notice = get_user_module_permissions(request.user, "notice")
    perms_payroll = get_user_module_permissions(request.user, "payroll")

    # 1. Timetable Schedule
    timetable = []
    next_class = None
    timetable_day = get_today_timetable_day()

    if perms_tt.get('can_view') and timetable_day:
        today_slots = (
            TimetableSlot.objects
            .filter(
                session=active_session,
                emp_id__iexact=teacher.emp_id,
                day_of_week=timetable_day.day_of_week
            )
            .order_by("period_no")
        )
        periods = TimetablePeriod.objects.filter(is_active=True, period_no__isnull=False)
        period_map = {p.period_no: p for p in periods}

        for slot in today_slots:
            period = period_map.get(slot.period_no)
            if period:
                start_time, end_time = period.start_time, period.end_time
                time_text = f"{start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}"
            else:
                start_time, end_time = None, None
                time_text = f"Period {slot.period_no}"

            item = {
                "id": slot.id,
                "period_no": slot.period_no,
                "class": (slot.class_field or "").strip(),
                "section": (slot.section or "").strip(),
                "subject": (slot.subject or "").strip(),
                "room": (slot.room or "—").strip(),
                "start_time": start_time,
                "end_time": end_time,
                "time": time_text,
            }
            timetable.append(item)

            if next_class is None and end_time is not None and current_time < end_time:
                next_class = item

    total_classes_today = len(timetable)

    # 2. Period 1 Attendance Assignment
    period_one_slot = None
    assigned_classes = []
    student_attendance = {
        "total": 0, "present": 0, "absent": 0, "leave": 0,
        "late": 0, "halfday": 0, "classes_marked": 0,
    }

    if perms_att.get('can_view') and timetable_day:
        period_one_slot = (
            TimetableSlot.objects
            .filter(
                session=active_session,
                emp_id__iexact=teacher.emp_id,
                day_of_week=timetable_day.day_of_week,
                period_no=1
            )
            .first()
        )

        if period_one_slot:
            attendance_class = (period_one_slot.class_field or "").strip()
            attendance_section = (period_one_slot.section or "").strip()
            attendance_subject = (period_one_slot.subject or "").strip()

            students_qs = get_student_queryset(attendance_class, attendance_section)
            student_count = students_qs.count()

            attendance_lock = (
                AttendanceLock.objects
                .filter(
                    session=active_session,
                    class_field__iexact=attendance_class,
                    section__iexact=attendance_section,
                    date=today
                )
                .first()
            )

            assigned_classes.append({
                "class": attendance_class,
                "section": attendance_section,
                "subject": attendance_subject,
                "student_count": student_count,
                "period_no": 1,
                "attendance_marked": bool(attendance_lock),
                "attendance_locked": bool(attendance_lock and attendance_lock.is_locked),
            })

            if attendance_lock:
                student_attendance["classes_marked"] = 1
                student_attendance["total"] = attendance_lock.total_students or 0
                student_attendance["present"] = attendance_lock.present_count or 0
                student_attendance["absent"] = attendance_lock.absent_count or 0
                student_attendance["leave"] = attendance_lock.leave_count or 0
                student_attendance["late"] = attendance_lock.late_count or 0
                student_attendance["halfday"] = attendance_lock.halfday_count or 0
            else:
                student_attendance["total"] = student_count

    total_assigned_classes = len(assigned_classes)

    # 3. Teacher's Own Monthly Attendance
    own_attendance_qs = (
        StaffAttendance.objects
        .filter(
            session=active_session,
            emp_id__iexact=teacher.emp_id,
            date__year=today.year,
            date__month=today.month
        )
    )
    own_present = own_attendance_qs.filter(status="P").count()
    own_absent = own_attendance_qs.filter(status="A").count()
    own_leave = own_attendance_qs.filter(status="L").count()
    own_late = own_attendance_qs.filter(status="T").count()
    own_halfday = own_attendance_qs.filter(status="H").count()
    own_working = own_attendance_qs.count()

    effective_present = own_present + own_late + (own_halfday * 0.5)
    own_attendance_percentage = round((effective_present / own_working) * 100, 1) if own_working else 0.0

    # 4. Exams & Marks Entry
    upcoming_exams = []
    marks_action_exams = []
    marks_to_enter_count = 0

    if perms_exam.get('can_view'):
        teacher_exams = CoreExam.objects.filter(teacher=teacher)
        upcoming_exams = teacher_exams.filter(exam_date__gte=today).order_by("exam_date", "start_time")[:5]
        marks_action_exams = teacher_exams.filter(exam_date__lte=today).order_by("-exam_date", "-start_time")[:5]
        marks_to_enter_count = teacher_exams.filter(exam_date__lte=today).count()

    # 5. Payroll
    latest_payroll = None
    if perms_payroll.get('can_view'):
        latest_payroll = (
            CoreStaffPayroll.objects
            .filter(teacher=teacher, employee_type="Teacher")
            .order_by("-payroll_year", "-payroll_month")
            .first()
        )

    # 6. Notices
    teacher_notices = []
    if perms_notice.get('can_view'):
        notice_queryset = (
            Notice.objects
            .filter(status="Published")
            .filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=today))
            .order_by("-pinned", "-created_at")
        )
        audience_words = {"teacher", "teachers", "staff", "all", "everyone"}
        for notice in notice_queryset[:30]:
            audience = notice.audience or []
            if isinstance(audience, str):
                audience = [audience]
            normalized_audience = {str(value).strip().lower() for value in audience}
            if not normalized_audience or normalized_audience.intersection(audience_words):
                teacher_notices.append(notice)
            if len(teacher_notices) >= 4:
                break

    context = {
        "teacher": teacher,
        "school": school,
        "today": today,
        "today_name": today.strftime("%A"),
        "active_session": active_session,
        # Schedule
        "timetable": timetable,
        "next_class": next_class,
        "total_classes_today": total_classes_today,
        # Attendance
        "period_one_slot": period_one_slot,
        "assigned_classes": assigned_classes,
        "total_assigned_classes": total_assigned_classes,
        "student_attendance": student_attendance,
        # Teacher Own Attendance
        "own_working": own_working,
        "own_present": own_present,
        "own_absent": own_absent,
        "own_leave": own_leave,
        "own_late": own_late,
        "own_halfday": own_halfday,
        "own_attendance_percentage": own_attendance_percentage,
        # Exams
        "upcoming_exams": upcoming_exams,
        "marks_action_exams": marks_action_exams,
        "marks_to_enter_count": marks_to_enter_count,
        # Payroll & Notices
        "latest_payroll": latest_payroll,
        "notices": teacher_notices,
        # Permissions Flags
        "perms_att": perms_att,
        "perms_exam": perms_exam,
        "perms_tt": perms_tt,
        "perms_notice": perms_notice,
        "perms_payroll": perms_payroll,
    }
    return render(request, "teacher_dashboard.html", context)
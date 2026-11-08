from datetime import datetime, date
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum

from .models import (
    CoreStudent,
    StudentAttendance,
    AttendanceSummary,
    CoreStudentFee,
    CoreExamMark,
    Notice,
    StudentTransport,
    TimetableSlot,
    TimetablePeriod,
    AcademicSession,
    SchoolProfile
)
from .user_rights import get_user_module_permissions


@login_required(login_url='login')
def student_dashboard_view(request):
    current_user = request.user
    
    # 1. Fetch Student (Admin check or direct roll/reg lookup)
    student_id = request.GET.get('student_id')
    student = None
    
    if student_id and (current_user.is_staff or current_user.is_superuser):
        student = CoreStudent.objects.filter(id=student_id).first()
    
    if not student:
        student = CoreStudent.objects.filter(
            Q(reg_no__iexact=current_user.username) | 
            Q(roll_no__iexact=current_user.username)
        ).first()

    if not student and current_user.is_superuser:
        student = CoreStudent.objects.filter(is_active=True).first()

    if not student:
        return render(request, "student_dashboard.html", {'error': 'No Student Record Found.'})

    # 2. Permissions for Student
    perms_accounts = get_user_module_permissions(request.user, "fee_record")
    perms_results = get_user_module_permissions(request.user, "results")
    perms_timetable = get_user_module_permissions(request.user, "timetable")
    perms_transport = get_user_module_permissions(request.user, "transport")
    perms_notice = get_user_module_permissions(request.user, "notice")
    perms_att = get_user_module_permissions(request.user, "attendance")

    active_session_obj = AcademicSession.objects.filter(is_current=True).first()
    active_session = active_session_obj.session_name if active_session_obj else "2026-2027"
    school_profile = SchoolProfile.objects.filter(is_active=True).first()

    today = date.today()
    current_month = today.month
    current_year = today.year

    # 3. Monthly Attendance
    working_days = present_days = absent_days = leave_days = 0
    attendance_percentage = 100.0

    if perms_att.get('can_view'):
        att_summary = AttendanceSummary.objects.filter(
            student=student,
            year=current_year,
            month=current_month
        ).first()

        if att_summary:
            working_days = att_summary.working_days
            present_days = att_summary.present_days
            absent_days = att_summary.absent_days
            leave_days = att_summary.leave_days
            attendance_percentage = float(att_summary.percentage)
        else:
            records = StudentAttendance.objects.filter(
                student=student,
                date__year=current_year,
                date__month=current_month
            )
            working_days = records.count()
            present_days = records.filter(status='P').count()
            absent_days = records.filter(status='A').count()
            leave_days = records.filter(status='L').count()
            attendance_percentage = round((present_days / working_days * 100), 1) if working_days > 0 else 100.0

    # 4. Fee Details (Only if user has accounts view right)
    latest_fee = None
    total_pending_balance = Decimal('0.00')
    if perms_accounts.get('can_view'):
        latest_fee = CoreStudentFee.objects.filter(student=student).order_by('-fee_year', '-fee_month').first()
        unpaid_fees = CoreStudentFee.objects.filter(student=student, status='Unpaid')
        total_pending_balance = unpaid_fees.aggregate(total=Sum('balance'))['total'] or Decimal('0.00')

    # 5. Today's Timetable
    day_of_week = today.isoweekday()
    day_names = {1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday', 5: 'Friday', 6: 'Saturday', 7: 'Sunday'}
    today_name = day_names.get(day_of_week, 'Monday')

    timetable_data = []
    if perms_timetable.get('can_view'):
        timetable_slots = TimetableSlot.objects.filter(
            class_field__iexact=student.student_class,
            section__iexact=student.section,
            day_of_week=day_of_week
        ).order_by('period_no')

        periods_map = {p.period_no: p for p in TimetablePeriod.objects.filter(is_active=True)}
        for slot in timetable_slots:
            period_info = periods_map.get(slot.period_no)
            time_str = f"{period_info.start_time.strftime('%I:%M %p')} - {period_info.end_time.strftime('%I:%M %p')}" if period_info else f"Period {slot.period_no}"
            timetable_data.append({
                'period_no': slot.period_no,
                'time_str': time_str,
                'subject': slot.subject,
                'teacher': slot.emp_id or 'Assigned Staff',
                'room': slot.room or 'Classroom'
            })

    # 6. Examination Results
    recent_marks = []
    if perms_results.get('can_view'):
        recent_marks = CoreExamMark.objects.filter(student=student).select_related('exam').order_by('-exam__exam_date')[:6]

    # 7. Transport Assignment
    transport_assignment = None
    if perms_transport.get('can_view'):
        transport_assignment = StudentTransport.objects.filter(
            student=student, 
            is_active=True
        ).select_related('vehicle', 'route', 'stop').first()

    # 8. Active Notices
    notices = []
    if perms_notice.get('can_view'):
        notices = Notice.objects.filter(status='Published').order_by('-pinned', '-created_at')[:4]

    context = {
        'student': student,
        'active_session': active_session,
        'school': school_profile,
        'today_date': today,
        'today_name': today_name,
        # Attendance
        'working_days': working_days,
        'present_days': present_days,
        'absent_days': absent_days,
        'leave_days': leave_days,
        'attendance_percentage': attendance_percentage,
        # Fees
        'latest_fee': latest_fee,
        'total_pending_balance': total_pending_balance,
        # Timetable
        'timetable': timetable_data,
        'total_periods_today': len(timetable_data),
        # Exams & Transport & Notices
        'recent_marks': recent_marks,
        'transport': transport_assignment,
        'notices': notices,
        # Permissions Flags
        'perms_accounts': perms_accounts,
        'perms_results': perms_results,
        'perms_timetable': perms_timetable,
        'perms_transport': perms_transport,
        'perms_notice': perms_notice,
        'perms_att': perms_att,
    }

    return render(request, "student_dashboard.html", context)
from datetime import date
from django.db.models import Count, Sum, Q
from django.shortcuts import render

from .models import (
    CoreStudent,
    CoreTeacher,
    CoreStaff,
    ClassDefination,
    Vehicle,
    StudentTransport,
    Route,
    CoreStudentFee,
    Notice,
    CoreExam,
    AcademicSession,
)
from .user_rights import get_user_module_permissions


def dashboard(request):
    today = date.today()
    month = today.month
    year = today.year

    # Evaluate permissions for the logged-in user
    perms_students = get_user_module_permissions(request.user, "students")
    perms_accounts = get_user_module_permissions(request.user, "accounts")
    perms_transport = get_user_module_permissions(request.user, "transport")
    perms_exam = get_user_module_permissions(request.user, "exam")
    perms_notice = get_user_module_permissions(request.user, "notice")

    # =========================================================
    # BASIC COUNTS
    # =========================================================
    s_students = CoreStudent.objects.filter(is_active=True).count()
    s_teachers = CoreTeacher.objects.filter(is_active=True).count()
    s_staff = CoreStaff.objects.filter(is_active=True).count()
    s_classes = ClassDefination.objects.count()
    s_riders = StudentTransport.objects.filter(is_active=True).count()
    s_routes = Route.objects.count()

    vehicles = list(Vehicle.objects.all())
    s_vehicles = len(vehicles)

    # =========================================================
    # FEE COLLECTION - CURRENT MONTH (Calculated if accounts permitted)
    # =========================================================
    fee_collected = 0
    fee_pending = 0
    fee_outstanding = 0
    fee_percent = 0

    if perms_accounts.get('can_view'):
        fees_this_month = CoreStudentFee.objects.filter(
            fee_month=month,
            fee_year=year,
        )

        fee_collected = (
            fees_this_month
            .filter(status="Paid")
            .aggregate(total=Sum("paid_amount"))
            .get("total")
            or 0
        )

        fee_pending = (
            fees_this_month
            .filter(status="Unpaid")
            .aggregate(total=Sum("balance"))
            .get("total")
            or 0
        )

        fee_outstanding = (
            CoreStudentFee.objects
            .filter(status="Unpaid")
            .aggregate(total=Sum("balance"))
            .get("total")
            or 0
        )

        total_due = fee_collected + fee_pending
        fee_percent = round((fee_collected / total_due) * 100) if total_due else 0
        fee_percent = max(0, min(100, fee_percent))

    # =========================================================
    # CLASS STRENGTH
    # =========================================================
    strength_qs = list(
        CoreStudent.objects
        .filter(is_active=True)
        .values("student_class")
        .annotate(count=Count("id"))
        .order_by("student_class")
    )

    max_count = max(
        (item["count"] for item in strength_qs),
        default=1,
    )

    class_strength = [
        {
            "name": item["student_class"] or "Unassigned",
            "count": item["count"],
            "percent": round((item["count"] / max_count) * 100),
        }
        for item in strength_qs
    ]

    # =========================================================
    # TRANSPORT
    # =========================================================
    free_seats = sum(
        max(getattr(vehicle, "available_seats", 0) or 0, 0)
        for vehicle in vehicles
    )

    full_vehicles = sum(
        1
        for vehicle in vehicles
        if getattr(vehicle, "is_full", False)
    )

    # =========================================================
    # RECENT / UPCOMING DATA
    # =========================================================
    recent_payments = []
    if perms_accounts.get('can_view'):
        recent_payments = (
            CoreStudentFee.objects
            .filter(status="Paid")
            .select_related("student")
            .order_by("-payment_date")[:6]
        )

    recent_notices = []
    if perms_notice.get('can_view'):
        recent_notices = (
            Notice.objects
            .filter(status="Published")
            .order_by("-pinned", "-publish_date")[:5]
        )

    upcoming_exams = []
    if perms_exam.get('can_view'):
        upcoming_exams = (
            CoreExam.objects
            .filter(exam_date__gte=today)
            .order_by("exam_date")[:5]
        )
    
    curr_sess = AcademicSession.objects.filter(is_current=True).first()
    academic_year = curr_sess.session_name if curr_sess else "2026-2027"

    context = {
        'academic_year': academic_year,
        "s_students": s_students,
        "s_teachers": s_teachers,
        "s_staff": s_staff,
        "s_classes": s_classes,
        "s_vehicles": s_vehicles,
        "s_riders": s_riders,
        "s_routes": s_routes,

        # Fee section
        "fee_collected": fee_collected,
        "fee_pending": fee_pending,
        "fee_outstanding": fee_outstanding,
        "fee_percent": fee_percent,
        "current_month_name": today.strftime("%B"),
        "current_year": year,

        # Class strength
        "class_strength": class_strength,

        # Transport
        "free_seats": free_seats,
        "full_vehicles": full_vehicles,

        # Dashboard lists
        "recent_payments": recent_payments,
        "recent_notices": recent_notices,
        "upcoming_exams": upcoming_exams,

        # Date
        "today": today,

        # Module Permissions
        "perms_students": perms_students,
        "perms_accounts": perms_accounts,
        "perms_transport": perms_transport,
        "perms_exam": perms_exam,
        "perms_notice": perms_notice,
    }

    return render(request, "dashboard.html", context)


def dumy(request):
    return render(request, "dumy.html")
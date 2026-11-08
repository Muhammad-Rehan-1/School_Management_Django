from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import CoreStudent, CoreTeacher, CoreStaff
from django.db.models import Q
from django.views.decorators.cache import never_cache


def get_redirect_url_for_user(user):
    """User ke role ke mutabiq uska dashboard return karta hai"""
    if user.is_superuser:
        return "dashboard"

    student = CoreStudent.objects.filter(
        Q(roll_no__iexact=user.username) | Q(reg_no__iexact=user.username),
        is_active=True
    ).first()
    if student:
        return "student_dashboard"

    teacher = CoreTeacher.objects.filter(emp_id__iexact=user.username, is_active=True).first()
    if teacher:
        return "teacher_dashboard"

    staff = CoreStaff.objects.filter(emp_id__iexact=user.username, is_active=True).first()
    if staff:
        return "dashboard"

    return "dashboard"


@never_cache  # Browser is page ko cache nahi karega
def user_login(request):
    # ✅ Agar koi pehle se logged-in user login page par aaye (chahe back button se ya direct URL se),
    # toh uska purana session foran destroy kar dein taake dobara login zaroori ho.
    if request.user.is_authenticated and request.method == "GET":
        logout(request)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        if not username or not password:
            messages.error(request, "Username and password are required.")
            return render(request, "login.html")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, "Your account has been deactivated. Please contact admin.")
                return render(request, "login.html")

            login(request, user)

            if user.is_superuser:
                request.session['user_role'] = 'Super Admin'
                return redirect("dashboard")

            student = CoreStudent.objects.filter(
                Q(roll_no__iexact=username) | Q(reg_no__iexact=username),
                is_active=True
            ).first()
            if student:
                request.session['user_role'] = 'Student'
                request.session['student_id'] = student.id
                return redirect("student_dashboard")

            teacher = CoreTeacher.objects.filter(emp_id__iexact=username, is_active=True).first()
            if teacher:
                request.session['user_role'] = 'Teacher'
                request.session['teacher_id'] = teacher.id
                return redirect("teacher_dashboard")

            staff_mem = CoreStaff.objects.filter(emp_id__iexact=username, is_active=True).first()
            if staff_mem:
                request.session['user_role'] = staff_mem.role or 'Staff'
                request.session['staff_id'] = staff_mem.id
                return redirect("dashboard")

            return redirect("dashboard")
        else:
            messages.error(request, "Invalid Credentials! Please check your ID and Password.")

    return render(request, "login.html")


def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("login")
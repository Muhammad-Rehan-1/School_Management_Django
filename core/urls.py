from django.urls import path
from . import views, students, teachers, staff, accounts

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    # Students
    path("students/", students.student_list, name="student_list"),
    path("students/add/", students.student_create, name="student_create"),
    path("students/<int:pk>/edit/", students.student_update, name="student_update"),
    path("students/<int:pk>/toggle/", students.student_toggle_status, name="student_toggle_status"),
    path("students/<int:pk>/delete/", students.student_delete, name="student_delete"),

    # Teachers & Staff
    path("teachers/", teachers.teacher_list, name="teacher_list"),
    path("teachers/add/", teachers.teacher_create, name="teacher_create"),
    path("teachers/<int:pk>/edit/", teachers.teacher_update, name="teacher_update"),
    path("teachers/<int:pk>/toggle/", teachers.teacher_toggle_status, name="teacher_toggle_status"),
    path("teachers/<int:pk>/delete/", teachers.teacher_delete, name="teacher_delete"),
    path("staff/", staff.staff_list, name="staff_list"),
    path("staff/add/", staff.staff_create, name="staff_create"),
    path("staff/<int:pk>/edit/", staff.staff_update, name="staff_update"),
    path("staff/<int:pk>/toggle/", staff.staff_toggle_status, name="staff_toggle_status"),
    path("staff/<int:pk>/delete/", staff.staff_delete, name="staff_delete"),

    # Accounts & PDF Reports
    path("accounts/fees/", accounts.fee_records, name="fee_records"),
    path("accounts/fees/add/", accounts.add_fees, name="add_fees"),
    path("accounts/challan/<int:student_id>/", accounts.generate_challan, name="generate_challan"),
    path("accounts/challans/bulk/", accounts.generate_class_challans, name="generate_class_challans"),
    path("accounts/api/ledger/<int:student_id>/", accounts.student_fee_ledger_api, name="student_fee_ledger_api"),
    path("accounts/pdf/ledger/<int:student_id>/", accounts.download_student_ledger_pdf, name="download_student_ledger_pdf"),
    path("accounts/pdf/defaulters/", accounts.download_defaulters_pdf, name="download_defaulters_pdf"),
    path("accounts/fees/<int:fee_id>/edit/", accounts.update_fee_record, name="update_fee_record"),
]
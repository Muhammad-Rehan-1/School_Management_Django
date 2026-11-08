from django.urls import path

from core import promote_students, transport
from . import views, students, teachers, staff, accounts, class_defination, subject_defination, staff_payroll, notices, exam, results, reports, timetable, login, attendance, staff_attendance, user_rights, teacher_dashboard, student_dashboard
from . import accountant_coa, accountant_voucher, accountant_posting_config
urlpatterns = [



    path("dashboard/", views.dashboard, name="dashboard"),

    # Class Defination
    path("classes/", class_defination.class_section_list, name="class_section_list"),
    path("classes/update/", class_defination.update_class_section, name="update_class_section"),
    path("classes/delete/", class_defination.delete_class_section, name="delete_class_section"),
    path("classes/toggle-status/", class_defination.toggle_status, name="toggle_status"),

    # Subject Defination
    path('subjects/', subject_defination.subject_list, name='subject_list'),
    path('subjects/add/', subject_defination.add_subject, name='add_subject'),
    path('subjects/toggle-status/', subject_defination.toggle_subject_status, name='toggle_subject_status'),
    path('subjects/edit/', subject_defination.edit_subject, name='edit_subject'),
    path('subjects/delete/', subject_defination.delete_subject, name='delete_subject'),
    
    # Students
    path("students/", students.student_list, name="student_list"),
    path("students/add/", students.student_create, name="student_create"),
    path("students/<int:pk>/edit/", students.student_update, name="student_update"),
    path("students/<int:pk>/toggle/", students.student_toggle_status, name="student_toggle_status"),
    path("students/<int:pk>/delete/", students.student_delete, name="student_delete"),
    path("students/api/next-roll/", students.get_next_roll_no_api, name="get_next_roll_no_api"),
    path('students/api/next-roll/', students.get_next_roll_no_api, name='get_next_roll_no_api'),
    path('students/api/next-reg/', students.get_next_reg_no_api, name='get_next_reg_no_api'),
    path('students/api/sections/', students.get_class_sections_api, name='get_class_sections_api'),

    # Teachers
    path("teachers/", teachers.teacher_list, name="teacher_list"),
    path("teachers/add/", teachers.teacher_create, name="teacher_create"),
    path("teachers/<int:pk>/edit/", teachers.teacher_update, name="teacher_update"),
    path("teachers/<int:pk>/toggle/", teachers.teacher_toggle_status, name="teacher_toggle_status"),
    path("teachers/<int:pk>/delete/", teachers.teacher_delete, name="teacher_delete"),
    path("teachers/api/next-id/", teachers.get_next_teacher_id_api, name="get_next_teacher_id_api"),
    
    # Staff
    path("staff/", staff.staff_list, name="staff_list"),
    path("staff/add/", staff.staff_create, name="staff_create"),
    path("staff/<int:pk>/edit/", staff.staff_update, name="staff_update"),
    path("staff/<int:pk>/toggle/", staff.staff_toggle_status, name="staff_toggle_status"),
    path("staff/<int:pk>/delete/", staff.staff_delete, name="staff_delete"),
    path("staff/api/next-id/", staff.get_next_staff_id_api, name="get_next_staff_id_api"),
    path('staff/api/add-role/', staff.add_staff_role_api, name='add_staff_role_api'),

    # Staff Payroll Module
    path("staff/payroll/", staff_payroll.payroll_dashboard, name="payroll_dashboard"),
    path("staff/payroll/<int:payroll_id>/edit/", staff_payroll.update_payroll_entry, name="update_payroll_entry"),
    path("staff/payroll/<int:payroll_id>/disburse/", staff_payroll.disburse_payroll_entry, name="disburse_payroll_entry"),
    path("staff/payroll/<int:payroll_id>/delete/", staff_payroll.delete_payroll_entry, name="delete_payroll_entry"),
    path("staff/payroll/<int:payroll_id>/payslip/", staff_payroll.download_payslip_pdf, name="download_payslip_pdf"),

    path("accounts/fees/", accounts.fee_records, name="fee_records"),
    path("accounts/fees/add/", accounts.add_fees, name="add_fees"),
    path("accounts/fees/special-fee/add/", accounts.add_special_fee, name="add_special_fee"),
    path("accounts/fees/special-fee/<int:fee_id>/delete/", accounts.delete_special_fee, name="delete_special_fee"),
    path("accounts/fees/<int:fee_id>/edit/", accounts.update_fee_record, name="update_fee_record"),
    path("accounts/challan/<int:student_id>/", accounts.generate_challan, name="generate_challan"),
    path("accounts/challans/bulk/", accounts.generate_class_challans, name="generate_class_challans"),
    path("accounts/api/ledger/<int:student_id>/", accounts.student_fee_ledger_api, name="student_fee_ledger_api"),    
    path("accounts/pdf/ledger/<int:student_id>/", accounts.download_student_ledger_pdf, name="download_student_ledger_pdf"),
    path("accounts/pdf/defaulters/", accounts.download_defaulters_pdf, name="download_defaulters_pdf"),
   
    # Accounts & Student Fees
    
    path("accounts/fees/", accounts.fee_records, name="fee_records"),
    path("accounts/fees/add/", accounts.add_fees, name="add_fees"),
    path("accounts/fees/extra/", accounts.extra_fee_manager, name="extra_fee_manager"),
    path("accounts/fees/special-fee/add/", accounts.add_special_fee, name="add_special_fee"),
    path("accounts/fees/special-fee/<int:fee_id>/delete/", accounts.delete_special_fee, name="delete_special_fee"),
    path('accounts/fees/receipt/<int:fee_id>/', accounts.print_fee_receipt, name='print_fee_receipt'),
    path("accounts/fees/class-base-fee/set/", accounts.set_class_base_fee, name="set_class_base_fee"),
    path("accounts/api/class-fee/<str:class_name>/", accounts.get_class_fee_api, name="get_class_fee_api"),
    path('accounts/api/live-fee-search/', accounts.live_student_fee_search_api, name='live_student_fee_search_api'),
    path("accounts/api/class-fee/<str:class_name>/", accounts.get_class_fee_api, name="get_class_fee_api"),
    path('students/api/sections/', students.get_class_sections_api, name='get_class_sections_api'),
    path("accounts/api/ledger/<int:student_id>/", accounts.student_fee_ledger_api, name="student_fee_ledger_api"),
    path("accounts/pdf/ledger/<int:student_id>/", accounts.download_student_ledger_pdf, name="download_student_ledger_pdf"),
    
   # Transport

    path('transport/',transport.transport_page,name='transport_page'),
    path('transport/drivers/<int:pk>/detail/', transport.staff_detail_json, name='staff_detail_json'),
    path('transport/vehicles/add/', transport.add_vehicle,       name='add_vehicle'),
    path('transport/vehicles/<int:pk>/detail/', transport.vehicle_detail,   name='vehicle_detail'),
    path('transport/vehicles/<int:pk>/edit/',  transport.edit_vehicle,  name='edit_vehicle'),
    path('transport/vehicles/<int:pk>/delete/', transport.delete_vehicle,   name='delete_vehicle'),
    path('transport/routes/add/', transport.add_route, name='add_route'),
    path('transport/routes/<int:pk>/edit/', transport.edit_route,  name='edit_route'),
    path('transport/routes/<int:pk>/delete/', transport.delete_route, name='delete_route'),

    #student transport
    path('transport/api/student/', transport.api_student_by_roll, name='api_student_by_roll'),
    path('transport/api/route/<int:pk>/vehicles/', transport.api_route_vehicles, name='api_route_vehicles'),
    path('transport/api/students/suggest/', transport.api_student_suggest,name='api_student_suggest'),
    path('transport/assign/add/', transport.assign_student_transport, name='assign_student_transport'),
    path('transport/assign/<int:pk>/edit/', transport.edit_student_transport, name='edit_student_transport'),
    path('transport/assign/<int:pk>/unassign/', transport.unassign_student_transport, name='unassign_student_transport'),
    path('transport/assign/<int:pk>/reactivate/', transport.reactivate_student_transport, name='reactivate_student_transport'),
    path('transport/assign/<int:pk>/delete/', transport.delete_student_transport, name='delete_student_transport'),
    path('transport/assign/<int:pk>/detail/', transport.assignment_detail_json, name='assignment_detail_json'),
    
    #Notice
    path('notice/', notices.notice_board, name='notice_board'),
    path('notice/add/', notices.add_notice, name='add_notice'),
    path('notice/<int:pk>/edit/', notices.edit_notice, name='edit_notice'),
    path('notice/<int:pk>/delete/', notices.delete_notice, name='delete_notice'),
    path('category/add/', notices.add_category_ajax, name='add_category_ajax'),
    path('notice/<int:pk>/pin/', notices.toggle_pin_notice, name='toggle_pin_notice'),
    path('notice/<int:pk>/detail/', notices.notice_detail_json, name='notice_detail_json'),
    path('notice/<int:pk>/publish/', notices.publish_notice, name='publish_notice'),
    path('notice/<int:pk>/print/', notices.notice_print, name='notice_print'),
    
    # Exams
    path("exam/", exam.exam_dashboard, name="exam_dashboard"),
    path("exam/list/", exam.exam_list, name="exam_list"),
    path("exam/create/", exam.exam_create, name="exam_create"),
    path("exam/<int:exam_id>/marks/", exam.exam_marks, name="exam_marks"),
    path("exam/<int:exam_id>/delete/", exam.exam_delete, name="exam_delete"),
    path("exam/api/list/", exam.exam_list_api, name="exam_list_api"),
    path("exam/pdf/", exam.exam_list_pdf, name="exam_list_pdf"),
    path("exam/<int:exam_id>/marks/pdf/", exam.exam_marks_pdf, name="exam_marks_pdf"),
    path("exam/<int:exam_id>/edit/", exam.exam_edit, name="exam_edit"),
    
    # Results :
    path("results/", results.results_list, name="results_list"),
    path("results/api/students/", results.results_students_api, name="results_students_api"),
    path("results/<int:student_id>/", results.student_result, name="student_result"),
    path("results/<int:student_id>/chart/", results.student_result_chart_api, name="student_result_chart_api"),
    path("results/<int:student_id>/pdf/", results.student_result_pdf, name="student_result_pdf"),
    
    # Main reports dashboard view
    path('reports/', reports.reports_page, name='reports_page'),
    path('reports/api/data/', reports.report_data, name='report_data'),
    path('reports/print/', reports.report_print, name='report_print'),
    
    # Timetable
    path('timetable/', timetable.timetable_page, name='timetable_page'),
    path('timetable/api/data/', timetable.tt_data, name='tt_data'),
    path('timetable/api/save/', timetable.tt_save, name='tt_save'),
    path('timetable/busy/', timetable.tt_busy, name='tt_busy'),
    
    # Settings
    path('timetable/settings/', timetable.timetable_settings, name='tt_settings'),
    path('timetable/api/settings/', timetable.tt_settings_data, name='tt_settings_data'),
    path('timetable/api/save-periods/', timetable.tt_save_periods, name='tt_save_periods'),
    path('timetable/api/save-days/', timetable.tt_save_days, name='tt_save_days'),
    
    # Login URLS
    path("", login.user_login, name="login"),
    path("logout/", login.user_logout, name="logout"),
    
    # Attendance
    path('attendance/',              attendance.attendance_page,   name='attendance_page'),
    path('attendance/data/',         attendance.att_data,          name='att_data'),
    path('attendance/save/',         attendance.att_save,          name='att_save'),
    path('attendance/lock/',         attendance.att_lock,          name='att_lock'),
    path('attendance/report/',       attendance.att_report,        name='att_report'),

    # Staff Attendance
    path('staff-attendance/',          staff_attendance.staff_attendance_page, name='staff_attendance_page'),
    path('staff-attendance/data/',     staff_attendance.sa_data,               name='sa_data'),
    path('staff-attendance/save/',     staff_attendance.sa_save,               name='sa_save'),
    path('staff-attendance/lock/',     staff_attendance.sa_lock,               name='sa_lock'),
    path('staff-attendance/report/',   staff_attendance.sa_report,             name='sa_report'),
    path('staff-attendance/today/',    staff_attendance.sa_today_summary,      name='sa_today_summary'),
    path('staff-attendance/history/',  staff_attendance.sa_staff_history,      name='sa_staff_history'),

    # Holidays
    path('attendance/holidays/',     attendance.att_holidays,      name='att_holidays'),
    path('attendance/holiday/save/', attendance.att_holiday_save,  name='att_holiday_save'),

    # Extras (optional)
    path('attendance/today/',        attendance.att_today_summary, name='att_today_summary'),
    path('attendance/history/',      attendance.att_student_history, name='att_student_history'),
    
    # Promote students URLs
    path('students/promote/', promote_students.promote_students_view, name='promote_students'),
    path('students/promote/stage-draft/', promote_students.save_class_draft_api, name='save_class_draft_api'),
    path('students/promote/clear-draft/', promote_students.clear_all_drafts, name='clear_all_drafts'),
    path('students/promote/execute-session/', promote_students.execute_full_session_promotion, name='execute_full_session_promotion'),
    path('students/passouts/', promote_students.passout_students_view, name='passout_students_view'),
    path('students/passouts/revert/<int:alumni_id>/', promote_students.revert_passout_student, name='revert_passout_student'),


# User  Rights

    path("user-rights/", user_rights.user_rights_view, name="user_rights"),


# student dashboard

    path('student/dashboard/', student_dashboard.student_dashboard_view, name='student_dashboard'),

#teacher dashboard
    path("teacher/dashboard/", teacher_dashboard.teacher_dashboard_view, name="teacher_dashboard"),


# User Rights APIs
    path("accounts/api/class-student-count/", user_rights.get_class_student_count_api, name="class_student_count_api"),
    path("accounts/api/save-user-rights/", user_rights.save_user_rights_api, name="save_user_rights_api"),
    path('accounts/api/get-user-rights/', user_rights.get_user_rights_api, name='get_user_rights_api'),

    
    path("dumy/", views.dumy, name="dumy"),



# Chart of Accounts Level 1-4
    path("accountant/coa/level1/", accountant_coa.coa_level1, name="coa_level1"),
    path("accountant/coa/level1/edit/<int:pk>/", accountant_coa.coa_level1_edit, name="coa_level1_edit"),
    path("accountant/coa/level1/delete/<int:pk>/", accountant_coa.coa_level1_delete, name="coa_level1_delete"),
    
    path("accountant/coa/level2/", accountant_coa.coa_level2, name="coa_level2"),
    path("accountant/coa/level2/edit/<int:pk>/", accountant_coa.coa_level2_edit, name="coa_level2_edit"),
    path("accountant/coa/level2/delete/<int:pk>/", accountant_coa.coa_level2_delete, name="coa_level2_delete"),
    
    path("accountant/coa/level3/", accountant_coa.coa_level3, name="coa_level3"),
    path("accountant/coa/level3/edit/<int:pk>/", accountant_coa.coa_level3_edit, name="coa_level3_edit"),
    path("accountant/coa/level3/delete/<int:pk>/", accountant_coa.coa_level3_delete, name="coa_level3_delete"),
    
    path("accountant/coa/level4/", accountant_coa.coa_level4, name="coa_level4"),
    path("accountant/coa/level4/edit/<str:account_id>/", accountant_coa.coa_level4_edit, name="coa_level4_edit"),
    path("accountant/coa/level4/delete/<str:account_id>/", accountant_coa.coa_level4_delete, name="coa_level4_delete"),
    
    # Posting Configuration
    path("accountant/settings/posting-config/", accountant_posting_config.posting_config, name="posting_config"),
    path("accountant/posting-config/", accountant_posting_config.posting_config), # Alias path for direct access

    # Accountant Module Routes & Aliases
    path("accountant/vouchers/new/", accountant_voucher.voucher_entry, name="voucher_entry"),
    # path("accountant/vouchers/", accountant_voucher.voucher_list, name="voucher_list"),
    path("accountant/vouchers/post/<str:voucher_no>/", accountant_voucher.post_voucher_to_ledger, name="post_voucher"),
    
    # General Ledger & Trial Balance with aliases
    path("accountant/reports/general-ledger/", accountant_voucher.general_ledger_report, name="general_ledger_report"),
    path("accountant/general-ledger/", accountant_voucher.general_ledger_report, name="general_ledger"),
    
    path("accountant/reports/trial-balance/", accountant_voucher.trial_balance_report, name="trial_balance_report"),
    path("accountant/trial-balance/", accountant_voucher.trial_balance_report, name="trial_balance"),
    path('accountant/bank-file/', accountant_voucher.bank_file_view, name='bank_file'),
    path('accountant/bank-file/edit/<int:bank_id>/', accountant_voucher.bank_file_edit, name='bank_file_edit'),
    path('accountant/bank-file/delete/<int:bank_id>/', accountant_voucher.bank_file_delete, name='bank_file_delete'),
    path('accountant/voucher-register/', accountant_voucher.voucher_register, name='voucher_register'),
    path('voucher-post/<str:voucher_no>/', accountant_voucher.post_voucher, name='post_voucher'),       # <--- views ki jagah accountant_voucher
    path('voucher-delete/<str:voucher_no>/', accountant_voucher.delete_voucher, name='delete_voucher'), # <--- views ki jagah accountant_voucher
    path("accountant/vouchers/journal/", accountant_voucher.journal_voucher_view, name="journal_voucher"),
    path("accountant/vouchers/submit/", accountant_voucher.submit_journal_voucher, name="submit_journal_voucher"),
    path('accountant/vouchers/print/<str:voucher_no>/', accountant_voucher.print_voucher, name='print_voucher'),
    
]  
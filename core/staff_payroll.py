import io
import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q, Sum
from django.contrib import messages
from django.db import transaction
from .models import CoreTeacher as Teacher, CoreStaff as Staff, CoreStaffPayroll as Payroll, AccCoaLevel4, AccBankMaster, AccVoucherSequence, AccVoucherMaster, AccVoucherDetail, AccGeneralLedger, AcademicSession
from .user_rights import get_user_module_permissions

# ReportLab Imports for Payslip PDF
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from xml.sax.saxutils import escape
from .context_processors import get_school_profile

MONTHS_DICT = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April',
    5: 'May', 6: 'June', 7: 'July', 8: 'August',
    9: 'September', 10: 'October', 11: 'November', 12: 'December'
}

def school_header(story, name_color='#1E2740'):
    school = get_school_profile()
    styles = getSampleStyleSheet()
    name_style = ParagraphStyle('SchoolName', parent=styles['Heading1'], fontSize=16, alignment=1,
                                textColor=colors.HexColor(name_color), spaceAfter=2)
    info_style = ParagraphStyle('SchoolInfo', parent=styles['Normal'], fontSize=8.5, alignment=1,
                                textColor=colors.HexColor('#9AA1B2'), spaceAfter=4)
    story.append(Paragraph(f"<b>{escape(school['school_name'].upper())}</b>", name_style))
    info = '  |  '.join(filter(None, [
        school['campus_name'], school['address'],
        f"Ph: {school['phone_number']}" if school['phone_number'] else '',
        school['email'],
    ]))
    if info:
        story.append(Paragraph(escape(info), info_style))


def _years_from_session_name(sess_name: str):
    try:
        a, b = sess_name.split('-')
        a, b = int(a.strip()), int(b.strip())
        if a <= b:
            return list(range(a, b + 1))
    except Exception:
        pass
    y = datetime.date.today().year
    return [y, y + 1]

def payroll_dashboard(request):
    # ================= RIGHTS CHECK: VIEW =================
    perms = get_user_module_permissions(request.user, "payroll")
    if not perms.get('can_view'):
        messages.error(request, "Access Denied: You do not have permission to view Staff Payroll.")
        return redirect('dashboard')

    current_date = datetime.date.today()
    active_tab = request.GET.get('tab', 'teachers').strip()
    status_filter = request.GET.get('status', 'all').strip()
    search_query = request.GET.get('q', '').strip()
    today = datetime.date.today()

    # ✅ 1. Active Current Session ko Priority dein
    current_sess = AcademicSession.objects.filter(is_current=True).order_by('-id').first()
    if current_sess and current_sess.session_name:
        current_sess_name = current_sess.session_name.strip()
    else:
        # Fallback to current calendar session
        current_sess_name = f"{today.year}-{today.year+1}"

    # Sessions list ko chronological order mein load karein
    all_sessions_qs = AcademicSession.objects.all().order_by('session_name').values_list('session_name', flat=True)
    all_sessions = [s.strip() for s in all_sessions_qs if s]
    if not all_sessions:
        all_sessions = [current_sess_name]

    # ✅ 2. Agar URL mein session pass nahi hua to strictly ACTIVE session select ho
    selected_session = (request.GET.get('session') or '').strip()
    if not selected_session or selected_session not in all_sessions:
        selected_session = current_sess_name

    session_years = _years_from_session_name(selected_session)

    selected_month = int(request.GET.get('month', today.month))
    # Default year active session ka saal banega
    default_year = today.year if today.year in session_years else session_years[0]
    selected_year = int(request.GET.get('year', default_year))

    teachers = Teacher.objects.filter(is_active=True)
    for t in teachers:
        p, created = Payroll.objects.get_or_create(
            payroll_month=selected_month,
            payroll_year=selected_year,
            employee_type='Teacher',
            teacher=t,
            defaults={
                'basic_salary': t.salary or Decimal('0.00'),
                'extra_allowance': Decimal('0.00'),
                'deduction': Decimal('0.00'),
                'net_salary': t.salary or Decimal('0.00'),
                'status': 'Pending'
            }
        )
        if not created and p.status == 'Pending' and p.basic_salary != t.salary:
            p.basic_salary = t.salary or Decimal('0.00')
            p.net_salary = max(Decimal('0.00'), p.basic_salary + p.extra_allowance - p.deduction)
            p.save()

    staff_members = Staff.objects.filter(is_active=True)
    for s in staff_members:
        p, created = Payroll.objects.get_or_create(
            payroll_month=selected_month,
            payroll_year=selected_year,
            employee_type='Staff',
            staff=s,
            defaults={
                'basic_salary': s.salary or Decimal('0.00'),
                'extra_allowance': Decimal('0.00'),
                'deduction': Decimal('0.00'),
                'net_salary': s.salary or Decimal('0.00'),
                'status': 'Pending'
            }
        )
        if not created and p.status == 'Pending' and p.basic_salary != s.salary:
            p.basic_salary = s.salary or Decimal('0.00')
            p.net_salary = max(Decimal('0.00'), p.basic_salary + p.extra_allowance - p.deduction)
            p.save()

    teachers_payroll = Payroll.objects.select_related('teacher').filter(
        payroll_month=selected_month,
        payroll_year=selected_year,
        employee_type='Teacher',
        teacher__is_active=True
    ).order_by('-id')

    staff_payroll = Payroll.objects.select_related('staff').filter(
        payroll_month=selected_month,
        payroll_year=selected_year,
        employee_type='Staff',
        staff__is_active=True
    ).order_by('-id')

    if status_filter == 'paid':
        teachers_payroll = teachers_payroll.filter(status='Paid')
        staff_payroll = staff_payroll.filter(status='Paid')
    elif status_filter == 'pending':
        teachers_payroll = teachers_payroll.filter(status='Pending')
        staff_payroll = staff_payroll.filter(status='Pending')

    if search_query:
        teachers_payroll = teachers_payroll.filter(
            Q(teacher__name__icontains=search_query) |
            Q(teacher__emp_id__icontains=search_query) |
            Q(teacher__subject__icontains=search_query)
        )
        staff_payroll = staff_payroll.filter(
            Q(staff__name__icontains=search_query) |
            Q(staff__emp_id__icontains=search_query) |
            Q(staff__role__icontains=search_query)
        )

    all_current_payrolls = Payroll.objects.filter(
        payroll_month=selected_month, 
        payroll_year=selected_year
    ).filter(
        Q(teacher__is_active=True) | Q(staff__is_active=True)
    )
    total_payroll_amount = all_current_payrolls.aggregate(Sum('net_salary'))['net_salary__sum'] or Decimal('0.00')
    total_paid_amount = all_current_payrolls.filter(status='Paid').aggregate(Sum('net_salary'))['net_salary__sum'] or Decimal('0.00')
    total_pending_amount = total_payroll_amount - total_paid_amount

    paid_count = all_current_payrolls.filter(status='Paid').count()
    pending_count = all_current_payrolls.filter(status='Pending').count()

    # === YEH DO LINES ADD KARNA ZAROORI HAI ===
    cash_account = AccCoaLevel4.objects.filter(is_cash=True, status='Active').first()
    bank_accounts = AccBankMaster.objects.filter(is_active=True).select_related('account')

    context = {
        'selected_month': selected_month,
        'selected_month_name': MONTHS_DICT.get(selected_month),
        'selected_year': selected_year,
        'session_years': session_years,
        'selected_session': selected_session,
        'all_academic_sessions': all_sessions,
        'months': MONTHS_DICT,
        'years': session_years if session_years else [current_date.year - 1, current_date.year, current_date.year + 1],
        'active_tab': active_tab,
        'status_filter': status_filter,
        'search_query': search_query,
        'teachers_payroll': teachers_payroll,
        'staff_payroll': staff_payroll,
        'total_payroll_amount': total_payroll_amount,
        'total_paid_amount': total_paid_amount,
        'total_pending_amount': total_pending_amount,
        'paid_count': paid_count,
        'pending_count': pending_count,
        
        # === YEH DO LINES BHI CONTEXT MEIN ADD KAREIN ===
        'cash_account': cash_account,       
        'bank_accounts': bank_accounts,     
        
        'perms': perms,
    }
    return render(request, "staff_payroll.html", context)




def update_payroll_entry(request, payroll_id):
    # ================= RIGHTS CHECK: EDIT =================
    perms = get_user_module_permissions(request.user, "payroll")
    if not perms.get('can_edit'):
        messages.error(request, "Access Denied: You do not have permission to modify payroll entries.")
        return redirect("payroll_dashboard")

    payroll = get_object_or_404(Payroll, id=payroll_id)
    if request.method == "POST":
        master_salary = payroll.teacher.salary if payroll.teacher else payroll.staff.salary
        extra = Decimal(request.POST.get('extra_allowance', '0.00'))
        deduct = Decimal(request.POST.get('deduction', '0.00'))
        
        payroll.basic_salary = master_salary
        payroll.extra_allowance = extra
        payroll.deduction = deduct
        payroll.net_salary = max(Decimal('0.00'), master_salary + extra - deduct)
        payroll.remarks = request.POST.get('remarks') or ''
        payroll.save()

        emp_name = payroll.teacher.name if payroll.teacher else (payroll.staff.name if payroll.staff else 'Employee')
        messages.success(request, f"Allowances and deductions updated for {emp_name}!")
        return redirect(f"/staff/payroll/?month={payroll.payroll_month}&year={payroll.payroll_year}&tab={'teachers' if payroll.employee_type == 'Teacher' else 'staff'}")

    return redirect("payroll_dashboard")


@transaction.atomic
def disburse_payroll_entry(request, payroll_id):
    # ================= RIGHTS CHECK: ADD/DISBURSE =================
    perms = get_user_module_permissions(request.user, "payroll")
    if not perms.get('can_add') and not perms.get('can_edit') and not request.user.is_superuser:
        messages.error(request, "Access Denied: You do not have permission to disburse salary payments.")
        return redirect("payroll_dashboard")

    payroll = get_object_or_404(Payroll, id=payroll_id)
    
    if request.method == "POST":
        pay_date_str = request.POST.get('payment_date')
        payment_date = datetime.datetime.strptime(pay_date_str, '%Y-%m-%d').date() if pay_date_str else datetime.date.today()
        
        source_account_id = request.POST.get('payment_source_id')
        disburse_remarks = request.POST.get('disburse_remarks', '')

        if not source_account_id:
            messages.error(request, "Error: Please select a valid Cash or Bank account to pay from.")
            return redirect(f"/staff/payroll/?month={payroll.payroll_month}&year={payroll.payroll_year}")

        # 1. Find the selected Bank or Cash Account (Credit)
        source_account = AccCoaLevel4.objects.filter(account_id=source_account_id).first()
        if not source_account:
            messages.error(request, "Selected payment account not found in Chart of Accounts.")
            return redirect(f"/staff/payroll/?month={payroll.payroll_month}&year={payroll.payroll_year}")

        # Determine Voucher Type (BPV for Bank, CPV for Cash)
        v_type = 'BPV' if source_account.is_bank else 'CPV'
        payment_method_name = source_account.account_name
        
        # Prevent paying the same payroll record twice.
        if payroll.status == "Paid":
            messages.error(request, "This payroll entry has already been paid.")
            return redirect(
                f"/staff/payroll/?month={payroll.payroll_month}"
                f"&year={payroll.payroll_year}"
            )

        # Only allow active cash or bank accounts.
        source_account = AccCoaLevel4.objects.filter(
            account_id=source_account_id,
            status="Active",
        ).first()

        if not source_account or not (
            source_account.is_cash or source_account.is_bank
        ):
            messages.error(request, "Select a valid active cash or bank account.")
            return redirect(
                f"/staff/payroll/?month={payroll.payroll_month}"
                f"&year={payroll.payroll_year}"
            )

        # 2. Find Salary Expense Account (Debit)
        # Yeh line 'SALARY' ke naam se Level 4 account dhoondegi (Expense Series aam tor par 05 se shuru hoti hai)
        # is_bank=False aur is_cash=False lagane se system strictly Expense account hi uthayega
        salary_expense_acc = AccCoaLevel4.objects.filter(
            account_name__icontains='SALARY', 
            is_bank=False, 
            is_cash=False
        ).first()
        if not salary_expense_acc:
            messages.error(request, "No 'Salary Expense' account found in Chart of Accounts! Please create one in Level 4 first.")
            return redirect(f"/staff/payroll/?month={payroll.payroll_month}&year={payroll.payroll_year}")

        try:
            # 3. Generate Unique Voucher No
            fiscal_year = f"{payment_date.year}-{payment_date.year+1}" if payment_date.month >= 7 else f"{payment_date.year-1}-{payment_date.year}"
            seq, _ = AccVoucherSequence.objects.get_or_create(
                voucher_type=v_type, fiscal_year=fiscal_year, defaults={'last_sequence': 0}
            )
            seq.last_sequence += 1
            seq.save()
            voucher_no = f"{v_type}-{fiscal_year}-{seq.last_sequence:05d}"

            emp_name = payroll.teacher.name if payroll.teacher else payroll.staff.name
            narration = f"Salary paid to {emp_name} for {MONTHS_DICT.get(payroll.payroll_month)} {payroll.payroll_year}"
            if disburse_remarks:
                narration += f" | {disburse_remarks}"

            # 4. Create Voucher Master
            master = AccVoucherMaster.objects.create(
                voucher_no=voucher_no,
                voucher_type=v_type,
                date=payment_date,
                description=narration,
                status='Posted',
                total_amount=payroll.net_salary,
                created_at=datetime.datetime.now()
            )

            # 5. Create Voucher Details & General Ledger Entries
            # Debit: Salary Expense Account
            AccVoucherDetail.objects.create(voucher=master, account=salary_expense_acc, debit=payroll.net_salary, credit=Decimal('0.00'), narration=narration)
            AccGeneralLedger.objects.create(voucher=master, account=salary_expense_acc, date=payment_date, debit=payroll.net_salary, credit=Decimal('0.00'), narration=narration, created_at=datetime.datetime.now())
            
            # Credit: Bank / Cash Account
            AccVoucherDetail.objects.create(voucher=master, account=source_account, debit=Decimal('0.00'), credit=payroll.net_salary, narration=narration)
            AccGeneralLedger.objects.create(voucher=master, account=source_account, date=payment_date, debit=Decimal('0.00'), credit=payroll.net_salary, narration=narration, created_at=datetime.datetime.now())

            # 6. Update Payroll Record
            payroll.status = 'Paid'
            payroll.payment_date = payment_date
            payroll.payment_method = payment_method_name
            payroll.remarks = narration
            payroll.save()

            messages.success(request, f"Salary of Rs. {payroll.net_salary} paid to {emp_name}. Auto-Voucher {voucher_no} generated!")
        
        except Exception as e:
            messages.error(request, f"Error processing salary payment: {str(e)}")

        return redirect(f"/staff/payroll/?month={payroll.payroll_month}&year={payroll.payroll_year}&tab={'teachers' if payroll.employee_type == 'Teacher' else 'staff'}")

    return redirect("payroll_dashboard")


def delete_payroll_entry(request, payroll_id):
    # ================= RIGHTS CHECK: DELETE =================
    perms = get_user_module_permissions(request.user, "payroll")
    if not perms.get('can_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete payroll records.")
        return redirect("payroll_dashboard")

    payroll = get_object_or_404(Payroll, id=payroll_id)
    month, year, tab = payroll.payroll_month, payroll.payroll_year, 'teachers' if payroll.employee_type == 'Teacher' else 'staff'
    if request.method == "POST":
        payroll.delete()
        messages.success(request, "Payroll entry deleted.")
    return redirect(f"/staff/payroll/?month={month}&year={year}&tab={tab}")


def download_payslip_pdf(request, payroll_id):
    # ================= RIGHTS CHECK: PRINT =================
    perms = get_user_module_permissions(request.user, "payroll")
    if not perms.get('can_print'):
        messages.error(request, "Access Denied: You do not have permission to download payslips.")
        return redirect("payroll_dashboard")

    payroll = get_object_or_404(Payroll, id=payroll_id)
    is_teacher = (payroll.employee_type == 'Teacher')
    emp = payroll.teacher if is_teacher else payroll.staff

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    story = []

    sub_style = ParagraphStyle('PaySub', parent=styles['Normal'], fontSize=10, alignment=1, textColor=colors.HexColor('#6B7280'))

    school_header(story, '#2C3752')
    story.append(Paragraph(f"<b>Official Salary Payslip — {MONTHS_DICT.get(payroll.payroll_month)} {payroll.payroll_year}</b>", sub_style))
    story.append(Spacer(1, 15))

    info_data = [
        [f"Employee Name: {emp.name}", f"Employee ID: {emp.emp_id}"],
        [f"Designation / Role: {emp.subject if is_teacher else emp.role}", f"Status: {payroll.status}"],
        [f"Contact: {emp.contact or '—'}", f"Payment Date: {payroll.payment_date.strftime('%d-%b-%Y') if payroll.payment_date else 'Pending'}"],
        [f"Payment Mode: {payroll.payment_method or 'Cash'}", f"Generated On: {datetime.date.today().strftime('%d-%b-%Y')}"]
    ]
    info_table = Table(info_data, colWidths=[265, 265])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8F9FC')),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E5E7EB')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#ECEEF3')),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 15))

    breakdown_data = [
        ["Description", "Earnings (Rs.)", "Deductions (Rs.)"],
        ["Basic Fixed Salary", f"{payroll.basic_salary}", "—"],
        ["Extra Allowance / Bonus", f"{payroll.extra_allowance}", "—"],
        ["Leaves / Penalty Deduction", "—", f"{payroll.deduction}"],
        ["TOTAL NET PAYABLE", "", f"Rs. {payroll.net_salary}"]
    ]
    pay_table = Table(breakdown_data, colWidths=[240, 145, 145])
    pay_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2C3752')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9.5),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#E8F7EF')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('TOPPADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(pay_table)
    story.append(Spacer(1, 15))

    if payroll.remarks:
        story.append(Paragraph(f"<b>Remarks / Note:</b> {escape(payroll.remarks)}", ParagraphStyle('Rmk', parent=styles['Normal'], fontSize=9.5, textColor=colors.HexColor('#374151'))))
        story.append(Spacer(1, 20))

    sig_data = [["_______________________", "_______________________"], ["Accountant Signature", "Employee Signature"]]
    sig_table = Table(sig_data, colWidths=[265, 265])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#6B7280')),
    ]))
    story.append(Spacer(1, 35))
    story.append(sig_table)

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Payslip_{emp.name}_{payroll.payroll_month}_{payroll.payroll_year}.pdf"'
    return response
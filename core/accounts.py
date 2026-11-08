import io
import json
import datetime
from decimal import Decimal
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Sum
from django.contrib import messages
from django.db import transaction
from django.utils import timezone

from .models import (
    CoreStudent as Student,
    CoreStudentFee as StudentFee,
    CoreClassSpecialFee as ClassSpecialFee,
    ClassDefination,
    CoreClassBaseFee as ClassBaseFee,
    FeeChallan,
    AcademicSession,
    # ✅ Partner ke Chart of Accounts & General Ledger Models
    AccSchoolPostingConfig,
    AccCoaLevel4,
    AccVoucherSequence,
    AccVoucherMaster,
    AccVoucherDetail,
    AccGeneralLedger,
)
from .user_rights import get_user_module_permissions

try:
    from .models import FeeChallanEditLog
except Exception:
    FeeChallanEditLog = None

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


# =============================================================
# HELPERS
# =============================================================

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

def get_current_session_name():
    s = AcademicSession.objects.filter(is_current=True).first()
    if s and s.session_name:
        return s.session_name
    today = datetime.date.today()
    return f"{today.year}-{today.year+1}"

def get_active_classes():
    return (
        ClassDefination.objects
        .filter(status__iexact='Active')
        .values_list('class_field', flat=True)
        .distinct()
        .order_by('class_field')
    )


def _school_header(story, name_color='#1E2740'):
    school = get_school_profile()
    styles = getSampleStyleSheet()

    name_style = ParagraphStyle(
        'SchoolName',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,
        textColor=colors.HexColor(name_color),
        spaceAfter=2
    )
    info_style = ParagraphStyle(
        'SchoolInfo',
        parent=styles['Normal'],
        fontSize=8.5,
        alignment=1,
        textColor=colors.HexColor('#9AA1B2'),
        spaceAfter=4
    )

    story.append(Paragraph(f"<b>{escape(school['school_name'].upper())}</b>", name_style))

    info = '  |  '.join(filter(None, [
        school['campus_name'],
        school['address'],
        f"Ph: {school['phone_number']}" if school['phone_number'] else '',
        school['email'],
    ]))
    if info:
        story.append(Paragraph(escape(info), info_style))


# =============================================================
# AUTO FEE VOUCHER POSTING HELPER (PARTNER INTEGRATION)
# =============================================================

def auto_post_fee_voucher(fee_record, amount_to_post=None, payment_method='Cash', bank_account_id=None):
    """
    Automatically creates and posts a CRV (Cash) or BRV (Bank/Wallet).
    Returns (True, "Success") or (False, "Error message").
    """
    try:
        if amount_to_post is not None:
            total_paid = Decimal(str(amount_to_post))
        else:
            total_paid = (fee_record.paid_amount or Decimal('0.00'))

        if total_paid <= Decimal('0.00'):
            return False, "Amount to post is zero."

        today = fee_record.payment_date or datetime.date.today()
        
        # --- SAFEGUARD: Agar kabhi date string form mein aa jaye toh usay convert kar do ---
        if isinstance(today, str):
            today = datetime.datetime.strptime(today, '%Y-%m-%d').date()
            
        fiscal_year = f"{today.year}-{today.year+1}" if today.month >= 7 else f"{today.year-1}-{today.year}"

        # ==========================================
        # STEP 1: IDENTIFY RECEIVING ACCOUNT (DEBIT)
        # ==========================================
        if payment_method != 'Cash' and bank_account_id:
            v_type = 'BRV'
            receive_account = AccCoaLevel4.objects.filter(account_id=bank_account_id).first()
            if not receive_account:
                return False, f"Selected Bank (ID: {bank_account_id}) not found in COA."
        else:
            v_type = 'CRV'
            # Fetch default Cash Account mapped in Posting Config (FEE_CASH)
            cash_config = AccSchoolPostingConfig.objects.filter(config_key='FEE_CASH').first()
            if cash_config and cash_config.account:
                receive_account = cash_config.account
            else:
                # Fallback to any account marked as 'is_cash=True'
                receive_account = AccCoaLevel4.objects.filter(is_cash=True).first()
            
            if not receive_account:
                return False, "No Cash Account mapped in Posting Config or COA."

        # ==========================================
        # STEP 2: IDENTIFY FEE INCOME ACCOUNT (CREDIT)
        # ==========================================
        # Fetch default Fee Income Account mapped in Posting Config (INCOME_TUITION)
        income_config = AccSchoolPostingConfig.objects.filter(config_key='INCOME_TUITION').first()
        if income_config and income_config.account:
            fee_income_account = income_config.account
        else:
            # STRONG FALLBACK: Grab the first Level 4 account that is neither Cash, Bank, Payable, nor Receivable.
            fee_income_account = AccCoaLevel4.objects.filter(
                is_cash=False, is_bank=False, is_payable=False, is_receivable=False
            ).first()

        if not fee_income_account:
            return False, "Fee Income Account is NOT mapped in Posting Config. Please map it first."

        # ==========================================
        # STEP 3: VOUCHER CREATION
        # ==========================================
        seq, _ = AccVoucherSequence.objects.get_or_create(
            voucher_type=v_type,
            fiscal_year=fiscal_year,
            defaults={'last_sequence': 0}
        )
        seq.last_sequence += 1
        seq.save()
        voucher_no = f"{v_type}-{fiscal_year}-{seq.last_sequence:05d}"

        narration_text = f"Fee received for {fee_record.student.name} (Challan: {fee_record.challan_no}) via {payment_method}"

        voucher_master = AccVoucherMaster.objects.create(
            voucher_no=voucher_no,
            voucher_type=v_type,
            date=today,
            description=narration_text,
            status='Posted',
            total_amount=total_paid,
            created_at=timezone.now()
        )

        AccVoucherDetail.objects.create(
            voucher=voucher_master, account=receive_account,
            debit=total_paid, credit=Decimal('0.00'), narration=narration_text
        )
        AccVoucherDetail.objects.create(
            voucher=voucher_master, account=fee_income_account,
            debit=Decimal('0.00'), credit=total_paid, narration=narration_text
        )

        AccGeneralLedger.objects.create(
            voucher=voucher_master, account=receive_account, date=today,
            debit=total_paid, credit=Decimal('0.00'), narration=narration_text, created_at=timezone.now()
        )
        AccGeneralLedger.objects.create(
            voucher=voucher_master, account=fee_income_account, date=today,
            debit=Decimal('0.00'), credit=total_paid, narration=narration_text, created_at=timezone.now()
        )

        return True, voucher_no

    except Exception as e:
        return False, str(e)

        


def get_month_special_charges(student_class, month, year):
    if not student_class:
        return Decimal('0.00'), ""
    special_records = ClassSpecialFee.objects.filter(
        Q(student_class__iexact=student_class.strip()) | Q(student_class__iexact='All'),
        fee_month=int(month),
        fee_year=int(year)
    )
    total_special = Decimal('0.00')
    titles = []
    for s in special_records:
        amt = s.amount or Decimal('0.00')
        total_special += amt
        titles.append(f"{s.title} (Rs. {amt})")

    return total_special, ", ".join(titles) if titles else "Exam / Special Charges"


def is_student_enrolled_for_month(student, target_month, target_year):
    enrol_date = student.enrolment_date or None
    if not enrol_date:
        return True
    if (target_year < enrol_date.year) or (target_year == enrol_date.year and target_month < enrol_date.month):
        return False
    return True


def iter_year_month(start_y, start_m, end_y, end_m):
    y, m = start_y, start_m
    while (y < end_y) or (y == end_y and m <= end_m):
        yield y, m
        m += 1
        if m == 13:
            m = 1
            y += 1


def sync_student_challans_upto(student, upto_month, upto_year):
    if not student.enrolment_date:
        get_or_create_backend_challan(student, upto_month, upto_year)
        return

    sy, sm = student.enrolment_date.year, student.enrolment_date.month
    if (upto_year < sy) or (upto_year == sy and upto_month < sm):
        return

    for y, m in iter_year_month(sy, sm, upto_year, upto_month):
        get_or_create_backend_challan(student, m, y)


def calculate_student_running_arrears(student, target_month, target_year):
    if not is_student_enrolled_for_month(student, target_month, target_year):
        return Decimal('0.00'), Decimal('0.00')

    unpaid_prior = FeeChallan.objects.filter(
        student=student,
        status__in=['Unpaid', 'Partial']
    ).filter(
        Q(fee_year__lt=target_year) | Q(fee_year=target_year, fee_month__lt=target_month)
    ).aggregate(Sum('balance'))['balance__sum'] or Decimal('0.00')

    prior_advance_challan = FeeChallan.objects.filter(
        student=student
    ).filter(
        Q(fee_year__lt=target_year) | Q(fee_year=target_year, fee_month__lt=target_month)
    ).order_by('-fee_year', '-fee_month').first()

    unadjusted_advance = (
        prior_advance_challan.advance_fee
        if (prior_advance_challan and (prior_advance_challan.advance_fee or 0) > 0)
        else Decimal('0.00')
    )

    return unpaid_prior, unadjusted_advance


def get_or_create_backend_challan(student, month, year):
    if not is_student_enrolled_for_month(student, month, year):
        return None

    existing = FeeChallan.objects.filter(student=student, fee_month=month, fee_year=year).first()
    if existing:
        # ✅ If old record has no snapshots, fill them (safe update)
        changed = False
        if not existing.session_name:
            existing.session_name = get_current_session_name()
            changed = True
        if not existing.class_field:
            existing.class_field = student.student_class
            changed = True
        if existing.section is None:
            existing.section = student.section or ''
            changed = True
        if not existing.roll_no:
            existing.roll_no = student.roll_no
            changed = True
        if changed:
            existing.save(update_fields=['session_name', 'class_field', 'section', 'roll_no'])
        return existing

    try:
        issue_date = datetime.date(year, month, 1)
        exp_days = int(getattr(student, "challan_expiry_days", None) or 8)
        exp_days = max(1, min(exp_days, 60))
        due_date = issue_date + timedelta(days=exp_days)
    except ValueError:
        issue_date = datetime.date.today()
        due_date = issue_date + datetime.timedelta(days=8)

    past_arrears, past_adv = calculate_student_running_arrears(student, month, year)

    # ✅ Snapshot class (important)
    class_snapshot = student.student_class
    section_snapshot = student.section or ''
    roll_snapshot = student.roll_no
    session_snapshot = get_current_session_name()

    special_chg, _ = get_month_special_charges(class_snapshot, month, year)

    tuition = student.monthly_fee or Decimal('0.00')
    transport = student.transport_charges or Decimal('0.00')

    admission = Decimal('0.00')
    if student.enrolment_date and student.enrolment_date.year == year and student.enrolment_date.month == month:
        admission = student.admission_fee or Decimal('0.00')

    month_billed = tuition + transport + admission + special_chg

    paid_from_adv = min(month_billed, past_adv)
    balance = max(Decimal('0.00'), month_billed - paid_from_adv)
    adv_left = max(Decimal('0.00'), past_adv - month_billed)

    status = 'Paid' if balance == 0 and month_billed > 0 else ('Partial' if paid_from_adv > 0 else 'Unpaid')
    challan_no = f"CH-{year}-{month:02d}-{student.id:04d}"

    challan = FeeChallan.objects.create(
        challan_no=challan_no,
        student=student,

        # ✅ NEW snapshot columns
        session_name=session_snapshot,
        class_field=class_snapshot,
        section=section_snapshot,
        roll_no=roll_snapshot,

        fee_month=month,
        fee_year=year,
        tuition_fee=tuition,
        transport_fee=transport,
        admission_fee=admission,
        other_charges=special_chg,
        fine=Decimal('0.00'),
        previous_arrears=past_arrears,
        total_amount=month_billed,
        paid_amount=paid_from_adv,
        advance_fee=adv_left,
        balance=balance,
        status=status,
        issue_date=issue_date,
        due_date=due_date,
        payment_date=(datetime.date.today() if paid_from_adv > 0 else None),
        payment_method=('Advance Credit' if paid_from_adv > 0 else None),
    )
    return challan
# =============================================================
# LIVE SEARCH API
# =============================================================

def live_student_fee_search_api(request):
    perms = get_user_module_permissions(request.user, "add_fees")
    if not perms.get('can_view'):
        return JsonResponse({'students': []}, status=403)

    query = request.GET.get('q', '').strip()
    selected_class = request.GET.get('class', '').strip()
    selected_month = int(request.GET.get('month', datetime.date.today().month))
    selected_year = int(request.GET.get('year', datetime.date.today().year))

    students = Student.objects.filter(is_active=True)
    if selected_class:
        students = students.filter(student_class__iexact=selected_class)
    if query:
        students = students.filter(
            Q(name__icontains=query) |
            Q(roll_no__icontains=query) |
            Q(reg_no__icontains=query) |
            Q(father_name__icontains=query)
        )

    results = []
    for stu in students[:35]:
        if not is_student_enrolled_for_month(stu, selected_month, selected_year):
            continue

        sync_student_challans_upto(stu, selected_month, selected_year)
        challan = get_or_create_backend_challan(stu, selected_month, selected_year)

        arrears, _ = calculate_student_running_arrears(stu, selected_month, selected_year)
        current_due = (challan.balance if challan else Decimal('0.00'))
        total_due = arrears + current_due

        paid_amt = challan.paid_amount if challan else Decimal('0.00')
        adv_amt = challan.advance_fee if challan else Decimal('0.00')

        special_chg, _ = get_month_special_charges(stu.student_class, selected_month, selected_year)
        st_status = 'Paid' if total_due <= 0 else ('Partial' if paid_amt > 0 else 'Unpaid')

        results.append({
            'id': stu.id,
            'name': stu.name,
            'father_name': stu.father_name,
            'student_class': stu.student_class,
            'roll_no': stu.roll_no,
            'reg_no': stu.reg_no or '—',
            'monthly_fee': str(stu.monthly_fee or '0.00'),
            'special_charges': str(special_chg),
            'paid_amount': str(paid_amt),
            'advance_fee': str(adv_amt),
            'unpaid': str(total_due),
            'status': st_status,
        })

    return JsonResponse({'students': results})


# =============================================================
# ADD FEES (FIFO) + AUTO GENERAL LEDGER POSTING
# =============================================================

def add_fees(request):
    perms = get_user_module_permissions(request.user, "add_fees")
    if not perms.get('can_view'):
        messages.error(request, "Access Denied: You do not have permission to access Fee Collection.")
        return redirect('dashboard')

    today = datetime.date.today()
    selected_month = int(request.GET.get('month', today.month))
    selected_year = int(request.GET.get('year', today.year))
    selected_class = request.GET.get('class', '').strip()
    search_query = request.GET.get('q', '').strip()

    students_data = []

    if search_query or selected_class:
        students = Student.objects.filter(is_active=True)
        if selected_class:
            students = students.filter(student_class__iexact=selected_class)
        if search_query:
            students = students.filter(
                Q(name__icontains=search_query) |
                Q(roll_no__icontains=search_query) |
                Q(reg_no__icontains=search_query) |
                Q(father_name__icontains=search_query)
            )

        for stu in students:
            if not is_student_enrolled_for_month(stu, selected_month, selected_year):
                continue

            sync_student_challans_upto(stu, selected_month, selected_year)

            challan = get_or_create_backend_challan(stu, selected_month, selected_year)
            special_chg, _ = get_month_special_charges(stu.student_class, selected_month, selected_year)

            arrears, _ = calculate_student_running_arrears(stu, selected_month, selected_year)
            current_due = challan.balance if challan else Decimal('0.00')
            total_due = arrears + current_due

            paid_amt = challan.paid_amount if challan else Decimal('0.00')
            adv_amt = challan.advance_fee if challan else Decimal('0.00')

            status = 'Paid' if total_due <= 0 else ('Partial' if paid_amt > 0 else 'Unpaid')

            students_data.append({
                'student': stu,
                'challan': challan,
                'monthly_total': (stu.monthly_fee or Decimal('0.00')) + (stu.transport_charges or Decimal('0.00')) + special_chg,
                'special_charges': special_chg,
                'paid_amount': paid_amt,
                'advance_fee': adv_amt,
                'unpaid': total_due,
                'status': status
            })

    if request.method == "POST" and "submit_payment" in request.POST:
        if not perms.get('can_add'):
            messages.error(request, "Access Denied: You do not have permission to receive or deposit fee payments.")
            return redirect('add_fees')

        student_id = request.POST.get('student_id')
        student = get_object_or_404(Student, id=student_id)
        month = int(request.POST.get('fee_month'))
        year = int(request.POST.get('fee_year'))

        incoming_payment = Decimal(request.POST.get('paid_amount') or '0.00')
        payment_method = request.POST.get('payment_method') or 'Cash'
        bank_account_id = request.POST.get('bank_account_id')
        
        # --- FIX: HTML Date String ko Proper Python Date mein convert karna ---
        pay_date_str = request.POST.get('payment_date')
        if pay_date_str:
            pay_date_val = datetime.datetime.strptime(pay_date_str, '%Y-%m-%d').date()
        else:
            pay_date_val = today
        # --------------------------------------------------------------------

        sync_student_challans_upto(student, month, year)
        get_or_create_backend_challan(student, month, year)

        allocated_cash = incoming_payment
        settled_details = []
        settled_challans_list = []

        with transaction.atomic():
            unpaid_prior_challans = FeeChallan.objects.filter(
                student=student,
                status__in=['Unpaid', 'Partial']
            ).filter(
                Q(fee_year__lt=year) | Q(fee_year=year, fee_month__lte=month)
            ).order_by('fee_year', 'fee_month')

            last_affected_challan = None

            for ch in unpaid_prior_challans:
                if allocated_cash <= Decimal('0.00'):
                    break

                due_on_challan = ch.balance or Decimal('0.00')
                if due_on_challan <= 0:
                    continue

                if allocated_cash >= due_on_challan:
                    ch.paid_amount = (ch.paid_amount or Decimal('0.00')) + due_on_challan
                    ch.balance = Decimal('0.00')
                    ch.status = 'Paid'
                    ch.payment_date = pay_date_val
                    ch.payment_method = payment_method
                    ch.save()

                    allocated_cash -= due_on_challan
                    settled_details.append(f"{MONTHS_DICT.get(ch.fee_month)} {ch.fee_year} (Paid Rs. {due_on_challan})")
                    last_affected_challan = ch
                    settled_challans_list.append((ch, due_on_challan))
                else:
                    ch.paid_amount = (ch.paid_amount or Decimal('0.00')) + allocated_cash
                    ch.balance = (ch.balance or Decimal('0.00')) - allocated_cash
                    ch.status = 'Partial'
                    ch.payment_date = pay_date_val
                    ch.payment_method = payment_method
                    ch.save()

                    settled_details.append(f"{MONTHS_DICT.get(ch.fee_month)} {ch.fee_year} (Partial Rs. {allocated_cash})")
                    settled_challans_list.append((ch, allocated_cash))
                    allocated_cash = Decimal('0.00')
                    last_affected_challan = ch
                    break

            if allocated_cash > Decimal('0.00'):
                current_m = month
                current_y = year

                if last_affected_challan:
                    last_affected_challan.advance_fee = allocated_cash
                    last_affected_challan.save(update_fields=['advance_fee'])

                while allocated_cash > Decimal('0.00'):
                    if current_m == 12:
                        current_m = 1
                        current_y += 1
                    else:
                        current_m += 1

                    next_ch = FeeChallan.objects.filter(student=student, fee_month=current_m, fee_year=current_y).first()
                    if not next_ch:
                        special_c, _ = get_month_special_charges(student.student_class, current_m, current_y)
                        tuition_val = student.monthly_fee or Decimal('0.00')
                        transport_val = student.transport_charges or Decimal('0.00')
                        month_bill = tuition_val + transport_val + special_c

                        next_ch = FeeChallan.objects.create(
                            challan_no=f"CH-{current_y}-{current_m:02d}-{student.id:04d}",
                            student=student,
                            fee_month=current_m,
                            fee_year=current_y,
                            tuition_fee=tuition_val,
                            transport_fee=transport_val,
                            admission_fee=Decimal('0.00'),
                            other_charges=special_c,
                            fine=Decimal('0.00'),
                            previous_arrears=Decimal('0.00'),
                            total_amount=month_bill,
                            paid_amount=Decimal('0.00'),
                            advance_fee=Decimal('0.00'),
                            balance=month_bill,
                            status='Unpaid',
                            issue_date=datetime.date(current_y, current_m, 1),
                            due_date=datetime.date(current_y, current_m, 8)
                        )

                    req_amount = next_ch.balance or Decimal('0.00')
                    if req_amount <= 0:
                        continue

                    if allocated_cash >= req_amount:
                        next_ch.paid_amount = (next_ch.paid_amount or Decimal('0.00')) + req_amount
                        next_ch.balance = Decimal('0.00')
                        next_ch.status = 'Paid'
                        allocated_cash -= req_amount
                        next_ch.advance_fee = allocated_cash
                        next_ch.payment_date = pay_date_val
                        next_ch.payment_method = payment_method
                        next_ch.save()
                        settled_details.append(f"{MONTHS_DICT.get(current_m)} {current_y} (Paid via Advance Rs. {req_amount})")
                        settled_challans_list.append((next_ch, req_amount))
                    else:
                        next_ch.paid_amount = (next_ch.paid_amount or Decimal('0.00')) + allocated_cash
                        next_ch.balance = max(Decimal('0.00'), req_amount - allocated_cash)
                        next_ch.advance_fee = Decimal('0.00')
                        next_ch.status = 'Partial'
                        next_ch.payment_date = pay_date_val
                        next_ch.payment_method = payment_method
                        next_ch.save()
                        settled_details.append(f"{MONTHS_DICT.get(current_m)} {current_y} (Partial via Advance Rs. {allocated_cash})")
                        settled_challans_list.append((next_ch, allocated_cash))
                        allocated_cash = Decimal('0.00')
                        break

            # --- PARTNER AUTO VOUCHER TRIGGER ---
            for c_obj, amount_received in settled_challans_list:
                is_success, v_result = auto_post_fee_voucher(
                    c_obj, 
                    amount_to_post=amount_received, 
                    payment_method=payment_method, 
                    bank_account_id=bank_account_id
                )
                
                if not is_success:
                    # Agar account missing hai toh Accountant ko warning dikhayega
                    messages.warning(request, f"Voucher Error for {c_obj.student.name}: {v_result}")
                else:
                    # Agar kamiyab ho gaya toh success message mein Voucher No dikhayega
                    messages.info(request, f"Voucher Generated: {v_result}") 
                    
            summary_msg = ", ".join(settled_details) if settled_details else f"Rs. {incoming_payment} processed."
            messages.success(request, f"Payment Processed! Allocation: {summary_msg}")

            target_id = last_affected_challan.id if last_affected_challan else 0
            return redirect(
                f"/accounts/fees/add/?month={month}&year={year}&class={student.student_class}"
                f"&q={student.roll_no}&print_receipt={target_id}&last_paid={incoming_payment}"
            )

    # add_fees view ke end par context se theek pehle yeh line add karein:
    active_banks = AccCoaLevel4.objects.filter(is_bank=True, status='Active').order_by('account_name')

    context = {
        'students_data': students_data,
        'search_query': search_query,
        'selected_month': selected_month,
        'selected_month_name': MONTHS_DICT.get(selected_month),
        'selected_year': selected_year,
        'selected_class': selected_class,
        'months': MONTHS_DICT,
        'years': [today.year - 1, today.year, today.year + 1],
        'available_classes': get_active_classes(),
        'active_banks': active_banks, # <--- YEH NAYI LINE ADD KI HAI
        'perms': perms,
    }
    return render(request, "accounts/add_fees.html", context)


# =============================================================
# LEDGER API
# =============================================================

def student_fee_ledger_api(request, student_id):
    perms = get_user_module_permissions(request.user, "fee_records")
    if not perms.get('can_view'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    student = get_object_or_404(Student, id=student_id)
    year = int(request.GET.get('year', datetime.date.today().year))
    range_filter = request.GET.get('range', 'all').strip()

    today = datetime.date.today()
    current_active_month = today.month if today.year == year else (12 if today.year > year else 0)

    if current_active_month > 0:
        sync_student_challans_upto(student, current_active_month, year)

    ledger = []
    carried_balance = Decimal('0.00')
    total_billed = Decimal('0.00')
    total_paid = Decimal('0.00')

    enrol_date = student.enrolment_date or datetime.date(year, 1, 1)

    for m in range(1, 13):
        if (year < enrol_date.year) or (year == enrol_date.year and m < enrol_date.month):
            continue

        ch = FeeChallan.objects.filter(student=student, fee_year=year, fee_month=m).first()

        if m > current_active_month and current_active_month > 0:
            if not ch or (ch.paid_amount or 0) <= 0:
                continue

        special_chg, _ = get_month_special_charges(student.student_class, m, year)

        if ch:
            month_fee = ch.total_amount or Decimal('0.00')
            paid_val = ch.paid_amount or Decimal('0.00')
            st_val = ch.status
            pay_date_txt = ch.payment_date.strftime('%A, %d-%b-%Y') if ch.payment_date else '—'
            method_txt = ch.payment_method or '—'
        else:
            admission = Decimal('0.00')
            if student.enrolment_date and student.enrolment_date.year == year and student.enrolment_date.month == m:
                admission = student.admission_fee or Decimal('0.00')

            month_fee = (student.monthly_fee or Decimal('0.00')) + (student.transport_charges or Decimal('0.00')) + admission + special_chg
            paid_val = Decimal('0.00')
            st_val = 'Unpaid'
            pay_date_txt = '—'
            method_txt = '—'

        prev_balance = carried_balance
        total_payable = prev_balance + month_fee
        closing_balance = max(Decimal('0.00'), total_payable - paid_val)

        carried_balance = closing_balance
        total_billed += month_fee
        total_paid += paid_val

        if current_active_month > 0 and m > current_active_month and paid_val > 0:
            adv_val = paid_val
        else:
            adv_val = (ch.advance_fee if ch else Decimal('0.00')) or Decimal('0.00')

        ledger.append({
            'month_no': m,
            'month': MONTHS_DICT.get(m),
            'prev_balance': str(prev_balance),
            'month_fee': str(month_fee),
            'total': str(total_payable),
            'paid': str(paid_val),
            'advance': str(adv_val),
            'balance': str(closing_balance),
            'status': st_val,
            'payment_date': pay_date_txt,
            'payment_method': method_txt,
        })

    if range_filter == 'current':
        ledger = [r for r in ledger if r['month_no'] == current_active_month]
    elif range_filter == '5months':
        ledger = ledger[-5:]
    elif range_filter == '10months':
        ledger = ledger[-10:]

    return JsonResponse({
        'student_id': student.id,
        'student_name': student.name,
        'father_name': student.father_name,
        'student_class': student.student_class,
        'roll_no': student.roll_no,
        'year': year,
        'total_billed': str(total_billed),
        'total_paid': str(total_paid),
        'total_balance': str(carried_balance),
        'ledger': ledger
    })


# =============================================================
# ADVANCE EDIT ENGINE
# =============================================================

def is_advance_paid(ch: FeeChallan) -> bool:
    if not ch.payment_date:
        return False
    try:
        month_start = datetime.date(ch.fee_year, ch.fee_month, 1)
    except Exception:
        return False
    return ch.payment_date < month_start


def adjust_student_future_advance(student, base_month, base_year, desired_advance_total, pay_date, pay_method):
    desired_advance_total = max(Decimal('0.00'), Decimal(desired_advance_total or 0))

    future_q = FeeChallan.objects.filter(student=student).filter(
        Q(fee_year__gt=base_year) | Q(fee_year=base_year, fee_month__gt=base_month)
    )

    future_list = list(future_q.order_by('fee_year', 'fee_month'))
    adv_paid = [ch for ch in future_list if (ch.paid_amount or 0) > 0 and is_advance_paid(ch)]
    current_total = sum((ch.paid_amount or Decimal('0.00')) for ch in adv_paid)

    affected = []

    if desired_advance_total < current_total:
        delta = current_total - desired_advance_total
        for ch in sorted(adv_paid, key=lambda x: (x.fee_year, x.fee_month), reverse=True):
            if delta <= 0:
                break

            can_remove = min(delta, ch.paid_amount or Decimal('0.00'))
            old_paid = ch.paid_amount or Decimal('0.00')

            ch.paid_amount = old_paid - can_remove
            ch.balance = min(ch.total_amount or Decimal('0.00'), (ch.balance or Decimal('0.00')) + can_remove)

            if ch.paid_amount <= 0:
                ch.paid_amount = Decimal('0.00')
                ch.status = 'Unpaid'
                ch.payment_date = None
                ch.payment_method = None
            else:
                ch.status = 'Partial'

            ch.save(update_fields=['paid_amount', 'balance', 'status', 'payment_date', 'payment_method'])

            affected.append({
                'fee_month': ch.fee_month,
                'fee_year': ch.fee_year,
                'old_paid': str(old_paid),
                'new_paid': str(ch.paid_amount),
            })
            delta -= can_remove

    elif desired_advance_total > current_total:
        delta = desired_advance_total - current_total

        y, m = base_year, base_month
        while delta > 0:
            if m == 12:
                m = 1
                y += 1
            else:
                m += 1

            ch = FeeChallan.objects.filter(student=student, fee_year=y, fee_month=m).first()
            if not ch:
                special_c, _ = get_month_special_charges(student.student_class, m, y)
                tuition_val = student.monthly_fee or Decimal('0.00')
                transport_val = student.transport_charges or Decimal('0.00')
                month_bill = tuition_val + transport_val + special_c

                _issue = datetime.date(y, m, 1)
                exp_days = int(getattr(student, "challan_expiry_days", None) or 8)
                exp_days = max(1, min(exp_days, 60))
                _due = _issue + timedelta(days=exp_days)

                ch = FeeChallan.objects.create(
                    challan_no=f"CH-{y}-{m:02d}-{student.id:04d}",
                    student=student,

                    session_name=get_current_session_name(),
                    class_field=student.student_class,
                    section=(student.section or ''),
                    roll_no=student.roll_no,

                    fee_month=m,
                    fee_year=y,
                    tuition_fee=tuition_val,
                    transport_fee=transport_val,
                    admission_fee=Decimal('0.00'),
                    other_charges=special_c,
                    fine=Decimal('0.00'),
                    previous_arrears=Decimal('0.00'),
                    total_amount=month_bill,
                    paid_amount=Decimal('0.00'),
                    advance_fee=Decimal('0.00'),
                    balance=month_bill,
                    status='Unpaid',
                    issue_date=_issue,
                    due_date=_due
                )

            if ch.status == 'Paid' and not is_advance_paid(ch):
                continue

            need = ch.balance or Decimal('0.00')
            if need <= 0:
                continue

            pay = min(need, delta)
            old_paid = ch.paid_amount or Decimal('0.00')

            ch.paid_amount = old_paid + pay
            ch.balance = max(Decimal('0.00'), need - pay)
            ch.status = 'Paid' if ch.balance == 0 else 'Partial'
            ch.payment_date = pay_date
            ch.payment_method = pay_method
            ch.save(update_fields=['paid_amount', 'balance', 'status', 'payment_date', 'payment_method'])

            affected.append({
                'fee_month': ch.fee_month,
                'fee_year': ch.fee_year,
                'old_paid': str(old_paid),
                'new_paid': str(ch.paid_amount),
            })
            delta -= pay

    return affected


# =============================================================
# CHALLAN GENERATION (SINGLE & BULK)
# =============================================================

def generate_challan(request, student_id):
    perms = get_user_module_permissions(request.user, "add_fees")
    if not perms.get('can_print'):
        messages.error(request, "Access Denied: You do not have permission to print fee challans.")
        return redirect('add_fees')

    student = get_object_or_404(Student, id=student_id)
    today = datetime.date.today()
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))

    sync_student_challans_upto(student, month, year)
    challan = get_or_create_backend_challan(student, month, year)
    if not challan:
        messages.info(request, f"Student {student.name} was not enrolled in {MONTHS_DICT.get(month)} {year}.")
        return redirect('add_fees')

    _, special_title = get_month_special_charges(student.student_class, month, year)

    arrears, _ = calculate_student_running_arrears(student, month, year)
    payable_now = (challan.balance or Decimal('0.00')) + arrears

    expiry_days = 8
    try:
        if challan and challan.issue_date and challan.due_date:
            expiry_days = (challan.due_date - challan.issue_date).days
    except Exception:
        pass
    challan_item = {
        'student': student,
        'fee': challan,
        'month_name': MONTHS_DICT.get(month),
        'issue_date': challan.issue_date,
        'due_date': challan.due_date,
        'past_arrears': arrears,
        'special_title': special_title,
        'is_advance_paid': False,
        'payable_now': payable_now,
        'expiry_days': expiry_days,

    }

    return render(request, "accounts/challan_pdf.html", {'challans': [challan_item]})


def generate_class_challans(request):
    perms = get_user_module_permissions(request.user, "add_fees")
    if not perms.get('can_print'):
        messages.error(request, "Access Denied: You do not have permission to generate bulk challans.")
        return redirect('add_fees')

    today = datetime.date.today()
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))
    selected_class = request.GET.get('class', '').strip()
    selected_section = request.GET.get('section', '').strip()

    students = Student.objects.filter(is_active=True).order_by('student_class', 'section', 'roll_no')
    if selected_class and selected_class != 'All Classes':
        students = students.filter(student_class__iexact=selected_class)
    if selected_section:
        students = students.filter(
            Q(section__iexact=selected_section) |
            Q(section__iexact=f"Section {selected_section}") |
            Q(section__icontains=selected_section)
        )

    has_enrolled_students = students.exists()
    challan_list = []

    for student in students:
        if not is_student_enrolled_for_month(student, month, year):
            continue

        sync_student_challans_upto(student, month, year)
        challan = get_or_create_backend_challan(student, month, year)
        if not challan:
            continue

        arrears, _ = calculate_student_running_arrears(student, month, year)
        payable_now = arrears + (challan.balance or Decimal('0.00'))

        if payable_now <= 0:
            continue

        _, special_title = get_month_special_charges(student.student_class, month, year)
        expiry_days = 8
        try:
            if challan and challan.issue_date and challan.due_date:
                expiry_days = (challan.due_date - challan.issue_date).days
        except Exception:
            pass
        challan_list.append({
            'student': student,
            'fee': challan,
            'month_name': MONTHS_DICT.get(month),
            'issue_date': challan.issue_date,
            'due_date': challan.due_date,
            'past_arrears': arrears,
            'special_title': special_title,
            'is_advance_paid': False,
            'payable_now': payable_now,
            'expiry_days': expiry_days,
        })

    context = {
        'challans': challan_list,
        'month_name': MONTHS_DICT.get(month),
        'year': year,
        'selected_class': selected_class,
        'selected_section': selected_section,
        'has_enrolled_students': has_enrolled_students,
    }
    return render(request, "accounts/challan_pdf.html", context)


# =============================================================
# FEE RECORDS
# =============================================================

def fee_records(request):
    perms = get_user_module_permissions(request.user, "fee_records")
    if not perms.get('can_view'):
        messages.error(request, "Access Denied: You do not have permission to view Fee Records.")
        return redirect('dashboard')

    today = datetime.date.today()

    total_receivable = Decimal('0.00')
    total_collected = Decimal('0.00')
    total_advance = Decimal('0.00')
    total_pending = Decimal('0.00')
    paid_pct = 0
    all_sessions = list(AcademicSession.objects.all().order_by('-id').values_list('session_name', flat=True))
    current_sess = AcademicSession.objects.filter(is_current=True).order_by('-id').first()

    if not current_sess and all_sessions:
        current_sess_name = all_sessions[0]
    elif current_sess:
        current_sess_name = current_sess.session_name
    else:
        current_sess_name = f"{today.year}-{today.year+1}"

    selected_session = (request.GET.get('session') or '').strip()
    if not selected_session:
        selected_session = current_sess_name

    if all_sessions and selected_session not in all_sessions:
        selected_session = current_sess_name

    session_years = _years_from_session_name(selected_session)

    selected_month = int(request.GET.get('month', today.month))
    default_year = today.year if today.year in session_years else session_years[0]
    selected_year = int(request.GET.get('year', default_year))

    selected_class = request.GET.get('class', '').strip()
    status_filter = request.GET.get('status', 'all').strip()
    active_students = Student.objects.filter(is_active=True)
    if selected_class:
        fees_qs = fees_qs.filter(class_field__iexact=selected_class)

    for st in active_students:
        sync_student_challans_upto(st, selected_month, selected_year)

    fees_qs = FeeChallan.objects.select_related('student').filter(
        fee_month=selected_month,
        fee_year=selected_year
    ).order_by('-id')

    if selected_session:
        fees_qs = fees_qs.filter(session_name__iexact=selected_session)

    fees = list(fees_qs)

    for f in fees:
        arrears, _ = calculate_student_running_arrears(f.student, selected_month, selected_year)
        f.display_arrears = arrears
        f.display_total_due = arrears + (f.balance or Decimal('0.00'))

        future_paid = FeeChallan.objects.filter(
            student=f.student,
            paid_amount__gt=0
        ).filter(
            Q(fee_year__gt=selected_year) |
            Q(fee_year=selected_year, fee_month__gt=selected_month)
        ).aggregate(Sum('paid_amount'))['paid_amount__sum'] or Decimal('0.00')

        direct_adv = f.advance_fee or Decimal('0.00')
        f.net_advance = max(future_paid, direct_adv)

        total_advance += f.net_advance
        total_receivable += (f.total_amount or Decimal('0.00'))
        total_collected += (f.paid_amount or Decimal('0.00'))
        total_pending += (f.display_total_due or Decimal('0.00'))

    if status_filter == 'paid':
        fees = [f for f in fees if (f.display_total_due or Decimal('0.00')) <= 0]
    elif status_filter == 'unpaid':
        fees = [f for f in fees if (f.display_total_due or Decimal('0.00')) > 0]

    if total_receivable > 0:
        paid_pct = int(round((total_collected / total_receivable) * 100))
    paid_pct = max(0, min(100, paid_pct))

    context = {
        'fees': fees,
        'selected_month': selected_month,
        'selected_month_name': MONTHS_DICT.get(selected_month),
        'selected_year': selected_year,
        'selected_class': selected_class,
        'status_filter': status_filter,
        'months': MONTHS_DICT,
        'years': [today.year - 1, today.year, today.year + 1],
        'total_receivable': total_receivable,
        'total_collected': total_collected,
        'total_advance': total_advance,
        'total_pending': total_pending,
        'paid_percentage': paid_pct,
        'available_classes': get_active_classes(),

        'selected_session': selected_session,
        'all_academic_sessions': all_sessions if all_sessions else [current_sess_name],
        'session_years': session_years,
        'perms': perms,
    }
    return render(request, "accounts/fee_records.html", context)


def update_fee_record(request, fee_id):
    perms = get_user_module_permissions(request.user, "fee_records")
    if not perms.get('can_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit fee records.")
        return redirect("fee_records")

    fee = get_object_or_404(FeeChallan, id=fee_id)

    if request.method == "POST":
        edit_reason = (request.POST.get('edit_reason') or '').strip()

        tuition = Decimal(request.POST.get('tuition_fee', '0.00'))
        transport = Decimal(request.POST.get('transport_fee', '0.00'))
        other = Decimal(request.POST.get('other_charges', '0.00'))
        fine = Decimal(request.POST.get('fine', '0.00'))

        paid = Decimal(request.POST.get('paid_amount', '0.00'))
        desired_future_advance = Decimal(request.POST.get('advance_fee', '0.00'))

        pay_date = request.POST.get('payment_date') or datetime.date.today()
        pay_method = request.POST.get('payment_method') or 'Cash'

        old_snapshot = {
            'tuition_fee': str(fee.tuition_fee),
            'transport_fee': str(fee.transport_fee),
            'other_charges': str(fee.other_charges),
            'fine': str(fee.fine),
            'total_amount': str(fee.total_amount),
            'paid_amount': str(fee.paid_amount),
            'advance_fee': str(fee.advance_fee),
            'balance': str(fee.balance),
            'status': fee.status,
        }

        current_total = tuition + transport + (fee.admission_fee or Decimal('0.00')) + other + fine
        fee.tuition_fee = tuition
        fee.transport_fee = transport
        fee.other_charges = other
        fee.fine = fine
        fee.total_amount = current_total

        fee.paid_amount = min(paid, current_total)
        fee.balance = max(Decimal('0.00'), current_total - fee.paid_amount)
        fee.status = 'Paid' if fee.balance == 0 and current_total > 0 else ('Partial' if fee.paid_amount > 0 else 'Unpaid')
        fee.payment_date = pay_date if fee.paid_amount > 0 else None
        fee.payment_method = pay_method if fee.paid_amount > 0 else None
        fee.save()

        # --- AUTO POSTING TRIGGER UPON EDIT RECORD MARKING PAID ---
        if fee.status == 'Paid':
            auto_post_fee_voucher(fee)

        affected = adjust_student_future_advance(
            student=fee.student,
            base_month=fee.fee_month,
            base_year=fee.fee_year,
            desired_advance_total=desired_future_advance,
            pay_date=pay_date,
            pay_method=pay_method
        )

        new_snapshot = {
            'tuition_fee': str(fee.tuition_fee),
            'transport_fee': str(fee.transport_fee),
            'other_charges': str(fee.other_charges),
            'fine': str(fee.fine),
            'total_amount': str(fee.total_amount),
            'paid_amount': str(fee.paid_amount),
            'advance_fee': str(desired_future_advance),
            'balance': str(fee.balance),
            'status': fee.status,
        }

        if FeeChallanEditLog and edit_reason:
            FeeChallanEditLog.objects.create(
                challan_id=fee.id,
                student_id=fee.student.id,
                edited_by=(request.user.username if request.user.is_authenticated else None),
                reason=edit_reason,
                old_data=json.dumps(old_snapshot),
                new_data=json.dumps(new_snapshot),
                affected=json.dumps(affected),
            )

        messages.success(request, f"Fee record updated for {fee.student.name}!")
        return redirect(f"/accounts/fees/?month={fee.fee_month}&year={fee.fee_year}")

    return redirect("fee_records")


# =============================================================
# EXTRA / EXAM FEE MODULE
# =============================================================

def extra_fee_manager(request):
    perms = get_user_module_permissions(request.user, "extra_fee")
    if not perms.get('can_view'):
        messages.error(request, "Access Denied: You do not have permission to view Extra / Exam Fees.")
        return redirect('dashboard')

    today = datetime.date.today()

    all_sessions = list(
        AcademicSession.objects.all()
        .order_by('-id')
        .values_list('session_name', flat=True)
    )
    current_sess = AcademicSession.objects.filter(is_current=True).order_by('-id').first()

    if not current_sess and all_sessions:
        current_sess_name = all_sessions[0]
    elif current_sess and current_sess.session_name:
        current_sess_name = current_sess.session_name
    else:
        current_sess_name = f"{today.year}-{today.year+1}"

    selected_session = (request.GET.get('session') or '').strip() or current_sess_name

    if all_sessions and selected_session not in all_sessions:
        selected_session = current_sess_name

    session_years = _years_from_session_name(selected_session)

    selected_month = int(request.GET.get('month', today.month))
    default_year = today.year if today.year in session_years else session_years[0]
    selected_year = int(request.GET.get('year', default_year))

    scheduled_special_fees = ClassSpecialFee.objects.filter(
        fee_year=selected_year
    ).order_by('fee_month', 'student_class')

    for sf in scheduled_special_fees:
        sf.month_name = MONTHS_DICT.get(int(sf.fee_month), f"Month {sf.fee_month}")

    class_base_fees = ClassBaseFee.objects.all().order_by('student_class')

    context = {
        'scheduled_special_fees': scheduled_special_fees,
        'class_base_fees': class_base_fees,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'selected_session': selected_session,
        'all_academic_sessions': all_sessions if all_sessions else [current_sess_name],
        'session_years': session_years,
        'months': MONTHS_DICT,
        'available_classes': get_active_classes(),
        'perms': perms,
    }
    return render(request, "accounts/extra_fee.html", context)


def add_special_fee(request):
    perms = get_user_module_permissions(request.user, "extra_fee")
    if not perms.get('can_add'):
        messages.error(request, "Access Denied: You do not have permission to schedule special charges.")
        return redirect("extra_fee_manager")

    if request.method == "POST":
        title = request.POST.get('title', '').strip()
        student_class = request.POST.get('student_class', '').strip()
        month = int(request.POST.get('fee_month'))
        year = int(request.POST.get('fee_year'))
        amount = Decimal(request.POST.get('amount') or '0.00')

        ClassSpecialFee.objects.create(
            title=title,
            student_class=student_class,
            fee_month=month,
            fee_year=year,
            amount=amount
        )

        class_filter = Q(student__student_class__iexact=student_class) if student_class != 'All' else Q()
        unpaid_challans = FeeChallan.objects.filter(class_filter, fee_month=month, fee_year=year, status__in=['Unpaid', 'Partial'])

        for ch in unpaid_challans:
            extra_chg, _ = get_month_special_charges(ch.student.student_class, month, year)
            ch.other_charges = extra_chg
            current_total = (ch.tuition_fee or 0) + (ch.transport_fee or 0) + (ch.admission_fee or 0) + (ch.other_charges or 0) + (ch.fine or 0)
            ch.total_amount = current_total
            ch.balance = max(Decimal('0.00'), current_total - (ch.paid_amount or 0))
            ch.status = 'Paid' if ch.balance == 0 and current_total > 0 else ('Partial' if (ch.paid_amount or 0) > 0 else 'Unpaid')
            ch.save()

        messages.success(request, f'Special Fee "{title}" (Rs. {amount}) scheduled & synchronized!')
        sess = (request.POST.get('session') or '').strip()
        return redirect(f"/accounts/fees/extra/?session={sess}&month={month}&year={year}")
    return redirect("extra_fee_manager")


def delete_special_fee(request, fee_id):
    perms = get_user_module_permissions(request.user, "extra_fee")
    if not perms.get('can_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete special charges.")
        return redirect("extra_fee_manager")

    special_fee = get_object_or_404(ClassSpecialFee, id=fee_id)
    month, year, target_class = special_fee.fee_month, special_fee.fee_year, special_fee.student_class

    if request.method == "POST":
        title = special_fee.title
        special_fee.delete()

        class_filter = Q(student__student_class__iexact=target_class) if target_class != 'All' else Q()
        unpaid_challans = FeeChallan.objects.filter(class_filter, fee_month=month, fee_year=year, status__in=['Unpaid', 'Partial'])

        for ch in unpaid_challans:
            extra_chg, _ = get_month_special_charges(ch.student.student_class, month, year)
            ch.other_charges = extra_chg
            current_total = (ch.tuition_fee or 0) + (ch.transport_fee or 0) + (ch.admission_fee or 0) + (ch.other_charges or 0) + (ch.fine or 0)
            ch.total_amount = current_total
            ch.balance = max(Decimal('0.00'), current_total - (ch.paid_amount or 0))
            ch.status = 'Paid' if ch.balance == 0 and current_total > 0 else ('Partial' if (ch.paid_amount or 0) > 0 else 'Unpaid')
            ch.save()

        messages.success(request, f'Special fee "{title}" removed.')
    return redirect(f"/accounts/fees/extra/?month={month}&year={year}")


def get_class_fee_api(request, class_name):
    fee_obj = ClassBaseFee.objects.filter(student_class__iexact=class_name).first()
    return JsonResponse({
        'class_name': class_name,
        'monthly_fee': str(fee_obj.monthly_fee) if fee_obj else '0.00',
        'admission_fee': str(fee_obj.admission_fee) if fee_obj else '0.00',
    })


def set_class_base_fee(request):
    perms = get_user_module_permissions(request.user, "extra_fee")
    if not perms.get('can_edit'):
        messages.error(request, "Access Denied: You do not have permission to modify base fee structures.")
        return redirect("extra_fee_manager")

    if request.method == "POST":
        student_class = request.POST.get('student_class', '').strip()
        monthly_fee = Decimal(request.POST.get('monthly_fee') or '0.00')
        admission_fee = Decimal(request.POST.get('admission_fee') or '0.00')

        ClassBaseFee.objects.update_or_create(
            student_class=student_class,
            defaults={'monthly_fee': monthly_fee, 'admission_fee': admission_fee}
        )

        Student.objects.filter(student_class__iexact=student_class).update(monthly_fee=monthly_fee)
        messages.success(request, f"Base fee for Class {student_class} updated.")
    return redirect("extra_fee_manager")


# =============================================================
# PDF: Student Ledger
# =============================================================

def download_student_ledger_pdf(request, student_id):
    perms = get_user_module_permissions(request.user, "fee_records")
    if not perms.get('can_print'):
        messages.error(request, "Access Denied: You do not have permission to export ledger statements.")
        return redirect('fee_records')

    student = get_object_or_404(Student, id=student_id)
    year = int(request.GET.get('year', datetime.date.today().year))
    today = datetime.date.today()
    current_active_month = today.month if today.year == year else (12 if today.year > year else 0)

    if current_active_month > 0:
        sync_student_challans_upto(student, current_active_month, year)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
    styles = getSampleStyleSheet()
    story = []

    sub_style = ParagraphStyle('DocSub', parent=styles['Normal'], fontSize=10, alignment=1, textColor=colors.HexColor('#555555'))

    _school_header(story, '#1E2740')
    story.append(Paragraph(f"<b>Annual Student Fee Statement — Academic Year {year}</b>", sub_style))
    story.append(Spacer(1, 14))

    info_data = [
        [f"Student Name: {student.name}", f"Class: {student.student_class} (Roll #{student.roll_no})"],
        [f"Father's Name: {student.father_name}", f"Contact: {student.contact or '—'}"],
        [f"Generated On: {datetime.date.today().strftime('%A, %d-%b-%Y')}", f"Status: {'Active' if student.is_active else 'Deactivated'}"]
    ]
    info_tab = Table(info_data, colWidths=[270, 270])
    info_tab.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8F9FC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E5E7EB')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#ECEEF3')),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(info_tab)
    story.append(Spacer(1, 14))

    table_data = [["Month", "Prev. Arrears", "Month Fee", "Total Payable", "Paid", "Advance", "Closing Balance", "Status"]]
    carried = Decimal('0.00')
    enrol_date = student.enrolment_date or datetime.date(year, 1, 1)

    for m in range(1, 13):
        if (year < enrol_date.year) or (year == enrol_date.year and m < enrol_date.month):
            continue

        ch = FeeChallan.objects.filter(student=student, fee_year=year, fee_month=m).first()
        if m > current_active_month and current_active_month > 0:
            if not ch or (ch.paid_amount or 0) <= 0:
                continue

        special_chg, _ = get_month_special_charges(student.student_class, m, year)

        if ch:
            month_fee = ch.total_amount or Decimal('0.00')
            paid_amt = ch.paid_amount or Decimal('0.00')
            status_txt = ch.status
        else:
            admission = Decimal('0.00')
            if student.enrolment_date and student.enrolment_date.year == year and student.enrolment_date.month == m:
                admission = student.admission_fee or Decimal('0.00')
            month_fee = (student.monthly_fee or Decimal('0.00')) + (student.transport_charges or Decimal('0.00')) + admission + special_chg
            paid_amt = Decimal('0.00')
            status_txt = 'Unpaid'

        total_payable = carried + month_fee
        closing = max(Decimal('0.00'), total_payable - paid_amt)

        adv_amt = paid_amt if (current_active_month > 0 and m > current_active_month and paid_amt > 0) else (ch.advance_fee if ch else Decimal('0.00'))

        table_data.append([
            MONTHS_DICT.get(m),
            f"Rs. {carried}",
            f"Rs. {month_fee}",
            f"Rs. {total_payable}",
            f"Rs. {paid_amt}",
            f"Rs. {adv_amt}",
            f"Rs. {closing}",
            status_txt
        ])

        carried = closing

    led_tab = Table(table_data, colWidths=[65, 70, 70, 75, 65, 65, 80, 55])
    led_tab.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E2740')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (1,0), (-2,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(led_tab)

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Ledger_{student.name}_{year}.pdf"'
    return response


# =============================================================
# PDF: Defaulters
# =============================================================

def download_defaulters_pdf(request):
    perms = get_user_module_permissions(request.user, "fee_records")
    if not perms.get('can_print'):
        messages.error(request, "Access Denied: You do not have permission to download Defaulters PDF.")
        return redirect('fee_records')

    today = datetime.date.today()
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))
    selected_class = request.GET.get('class', '').strip()

    fees = FeeChallan.objects.select_related('student').filter(
        fee_month=month, fee_year=year
    )
    today = datetime.date.today()
    fees = fees.filter(due_date__lt=today)  # ✅ only expired challans

    if selected_class:
        fees = fees.filter(class_field__iexact=selected_class)

    defaulters = []
    for ch in fees:
        arrears, _ = calculate_student_running_arrears(ch.student, month, year)
        total_due = arrears + (ch.balance or Decimal('0.00'))
        if total_due > 0 and (ch.due_date and ch.due_date < today):
            ch.total_due = total_due
            defaulters.append(ch)

    defaulters.sort(key=lambda x: (x.student.student_class, x.student.roll_no))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
    styles = getSampleStyleSheet()
    story = []

    sub_style = ParagraphStyle('DocSub', parent=styles['Normal'], fontSize=10, alignment=1, textColor=colors.HexColor('#555555'))

    _school_header(story, '#991B1B')
    story.append(Paragraph(f"<b>Official Defaulters & Pending Dues List — {MONTHS_DICT.get(month)} {year}</b>", sub_style))
    story.append(Spacer(1, 14))

    table_data = [["Roll #", "Student Name", "Father Name", "Class", "Current Fee", "Paid", "Total Due", "Contact"]]
    total_due = Decimal('0.00')

    for d in defaulters:
        total_due += d.total_due
        table_data.append([
            d.student.roll_no,
            d.student.name,
            d.student.father_name,
            d.student.student_class,
            f"Rs. {d.total_amount}",
            f"Rs. {d.paid_amount}",
            f"Rs. {d.total_due}",
            d.student.contact or '—'
        ])

    table_data.append(["TOTAL", "", "", "", "", "", f"Rs. {total_due}", ""])

    def_tab = Table(table_data, colWidths=[45, 95, 95, 55, 70, 60, 75, 55])
    def_tab.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#991B1B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (4,0), (6,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FEE2E2')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(def_tab)

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Defaulters_{MONTHS_DICT.get(month)}_{year}.pdf"'
    return response


# =============================================================
# POS RECEIPT
# =============================================================

def print_fee_receipt(request, fee_id):
    perms = get_user_module_permissions(request.user, "add_fees")
    if not perms.get('can_print'):
        messages.error(request, "Access Denied: You do not have permission to print receipts.")
        return redirect('add_fees')

    challan = get_object_or_404(FeeChallan, id=fee_id)
    school = get_school_profile()
    last_paid = request.GET.get('amount', challan.paid_amount)

    pay_date = challan.payment_date or datetime.date.today()
    day_name = pay_date.strftime('%A')
    formatted_date = pay_date.strftime('%d-%b-%Y')

    context = {
        'fee': challan,
        'student': challan.student,
        'school': school,
        'received_amount': last_paid,
        'day_name': day_name,
        'payment_date_formatted': formatted_date,
        'month_name': MONTHS_DICT.get(challan.fee_month),
    }
    return render(request, "accounts/pos_receipt.html", context)
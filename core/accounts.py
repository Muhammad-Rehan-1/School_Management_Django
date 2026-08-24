import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Sum
from django.contrib import messages
from .models import CoreStudent as Student, CoreStudentFee as StudentFee

MONTHS_DICT = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April',
    5: 'May', 6: 'June', 7: 'July', 8: 'August',
    9: 'September', 10: 'October', 11: 'November', 12: 'December'
}

# ==========================================
# 1. FEE RECORDS & AUTO-SYNC BY ADMISSION DATE
# ==========================================
def fee_records(request):
    current_date = datetime.date.today()
    selected_month = int(request.GET.get('month', current_date.month))
    selected_year = int(request.GET.get('year', current_date.year))
    selected_class = request.GET.get('class', '').strip()

    # Step 1: Filter students eligible for the selected month/year based on enrolment_date
    students_qs = Student.objects.all()
    if selected_class:
        students_qs = students_qs.filter(student_class__iexact=selected_class)

    for student in students_qs:
        # Check enrolment date to ensure student was admitted before or in this month
        if student.enrolment_date:
            enrol_year = student.enrolment_date.year
            enrol_month = student.enrolment_date.month
            if (selected_year < enrol_year) or (selected_year == enrol_year and selected_month < enrol_month):
                continue  # Skip months before student's admission

        challan_no = f"CH-{selected_year}{selected_month:02d}-{student.id:04d}"
        total = (student.monthly_fee or Decimal('0.00')) + \
                (student.transport_charges or Decimal('0.00')) + \
                (student.other_charges or Decimal('0.00'))

        StudentFee.objects.get_or_create(
            student=student,
            fee_month=selected_month,
            fee_year=selected_year,
            defaults={
                'challan_no': challan_no,
                'tuition_fee': student.monthly_fee or Decimal('0.00'),
                'transport_fee': student.transport_charges or Decimal('0.00'),
                'admission_fee': Decimal('0.00'),
                'other_charges': student.other_charges or Decimal('0.00'),
                'total_amount': total,
                'balance': total,
                'due_date': current_date + datetime.timedelta(days=10),
                'status': 'Unpaid'
            }
        )

    # Step 2: Fetch fee records
    fees_qs = StudentFee.objects.select_related('student').filter(
        fee_month=selected_month,
        fee_year=selected_year
    ).order_by('student__student_class', 'student__roll_no')

    if selected_class:
        fees_qs = fees_qs.filter(student__student_class__iexact=selected_class)

    total_generated = fees_qs.count()
    paid_count = fees_qs.filter(status='Paid').count()
    unpaid_count = fees_qs.filter(status__in=['Unpaid', 'Partial']).count()

    total_receivable = fees_qs.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
    total_collected = fees_qs.aggregate(Sum('paid_amount'))['paid_amount__sum'] or Decimal('0.00')
    total_advance = fees_qs.aggregate(Sum('advance_fee'))['advance_fee__sum'] or Decimal('0.00')
    total_pending = total_receivable - total_collected

    paid_percentage = round((paid_count / total_generated * 100)) if total_generated > 0 else 0
    unpaid_percentage = 100 - paid_percentage if total_generated > 0 else 0

    context = {
        "fees": fees_qs,
        "selected_month": selected_month,
        "selected_month_name": MONTHS_DICT.get(selected_month, ''),
        "selected_year": selected_year,
        "selected_class": selected_class,
        "months": MONTHS_DICT,
        "years": [current_date.year - 1, current_date.year, current_date.year + 1],
        
        "total_generated": total_generated,
        "paid_count": paid_count,
        "unpaid_count": unpaid_count,
        "paid_percentage": paid_percentage,
        "unpaid_percentage": unpaid_percentage,
        "total_receivable": total_receivable,
        "total_collected": total_collected,
        "total_advance": total_advance,
        "total_pending": total_pending,
    }
    return render(request, "accounts/fee_records.html", context)


# ==========================================
# 2. ADD FEES & ADVANCE PAYMENT PROCESSING
# ==========================================
def add_fees(request):
    current_date = datetime.date.today()
    search_query = request.GET.get('q', '').strip()
    selected_class = request.GET.get('class', '').strip()

    students_list = []
    if search_query or selected_class:
        raw_students = Student.objects.all().order_by('student_class', 'roll_no')
        if selected_class:
            raw_students = raw_students.filter(student_class__iexact=selected_class)
        if search_query:
            raw_students = raw_students.filter(
                Q(name__icontains=search_query) | 
                Q(roll_no__icontains=search_query) |
                Q(father_name__icontains=search_query)
            )

        for s in raw_students:
            # Check current month status
            fee = StudentFee.objects.filter(
                student=s, 
                fee_month=current_date.month, 
                fee_year=current_date.year
            ).first()

            if fee:
                unpaid_bal = fee.balance
                status = fee.status
            else:
                std_total = (s.monthly_fee or Decimal('0.00')) + (s.transport_charges or Decimal('0.00')) + (s.other_charges or Decimal('0.00'))
                unpaid_bal = std_total
                status = 'Unpaid'

            students_list.append({
                'student': s,
                'unpaid': unpaid_bal,
                'status': status,
                'monthly_total': (s.monthly_fee or Decimal('0.00')) + (s.transport_charges or Decimal('0.00')) + (s.other_charges or Decimal('0.00'))
            })

    # Payment Submission (Regular or Advance)
    if request.method == "POST" and "submit_payment" in request.POST:
        student_id = request.POST.get('student_id')
        fee_month = int(request.POST.get('fee_month', current_date.month))
        fee_year = int(request.POST.get('fee_year', current_date.year))
        paid_amount = Decimal(request.POST.get('paid_amount', '0.00'))
        is_advance = request.POST.get('is_advance', '0') == '1'
        payment_method = request.POST.get('payment_method', 'Cash')
        payment_date = request.POST.get('payment_date') or current_date
        notes = request.POST.get('notes', '')

        student = get_object_or_404(Student, id=student_id)
        challan_no = f"CH-{fee_year}{fee_month:02d}-{student.id:04d}"
        total = (student.monthly_fee or Decimal('0.00')) + (student.transport_charges or Decimal('0.00')) + (student.other_charges or Decimal('0.00'))

        fee_record, _ = StudentFee.objects.get_or_create(
            student=student,
            fee_month=fee_month,
            fee_year=fee_year,
            defaults={
                'challan_no': challan_no,
                'tuition_fee': student.monthly_fee or Decimal('0.00'),
                'transport_fee': student.transport_charges or Decimal('0.00'),
                'other_charges': student.other_charges or Decimal('0.00'),
                'total_amount': total,
                'balance': total,
                'due_date': current_date + datetime.timedelta(days=10),
                'status': 'Unpaid'
            }
        )

        if is_advance:
            fee_record.advance_fee += paid_amount
            fee_record.notes = (fee_record.notes or '') + f" | Advance: Rs. {paid_amount}"
        else:
            fee_record.paid_amount += paid_amount
            fee_record.balance = max(Decimal('0.00'), fee_record.total_amount - fee_record.paid_amount)
            if fee_record.balance == Decimal('0.00'):
                fee_record.status = 'Paid'
            elif fee_record.paid_amount > Decimal('0.00'):
                fee_record.status = 'Partial'

        fee_record.payment_date = payment_date
        fee_record.payment_method = payment_method
        if notes:
            fee_record.notes = notes
        fee_record.save()

        msg_type = "Advance Fee" if is_advance else "Fee"
        messages.success(request, f"{msg_type} of Rs. {paid_amount} recorded for {student.name}.")
        return redirect(f"{request.path}?q={student.roll_no}")

    context = {
        "students_data": students_list,
        "search_query": search_query,
        "selected_class": selected_class,
        "current_month": current_date.month,
        "current_year": current_date.year,
        "months": MONTHS_DICT,
    }
    return render(request, "accounts/add_fees.html", context)


# ==========================================
# 3. STUDENT YEARLY LEDGER (VIEW DETAIL JSON)
# ==========================================
def student_fee_ledger_api(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    current_year = datetime.date.today().year
    year = int(request.GET.get('year', current_year))

    records = StudentFee.objects.filter(student=student, fee_year=year).order_by('fee_month')
    
    ledger = []
    for r in records:
        ledger.append({
            'month': MONTHS_DICT.get(r.fee_month),
            'total': str(r.total_amount),
            'paid': str(r.paid_amount),
            'advance': str(r.advance_fee),
            'balance': str(r.balance),
            'status': r.status,
            'payment_date': r.payment_date.strftime('%d-%b-%Y') if r.payment_date else '—',
            'payment_method': r.payment_method or '—',
            'notes': r.notes or '—',
        })

    return JsonResponse({
        'student_name': student.name,
        'father_name': student.father_name,
        'student_class': student.student_class,
        'roll_no': student.roll_no,
        'year': year,
        'ledger': ledger
    })


# ==========================================
# 4. SINGLE CHALLAN PDF
# ==========================================
def generate_challan(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    current_date = datetime.date.today()
    month = int(request.GET.get('month', current_date.month))
    year = int(request.GET.get('year', current_date.year))

    challan_no = f"CH-{year}{month:02d}-{student.id:04d}"
    total = (student.monthly_fee or Decimal('0.00')) + (student.transport_charges or Decimal('0.00')) + (student.other_charges or Decimal('0.00'))

    fee_record, _ = StudentFee.objects.get_or_create(
        student=student,
        fee_month=month,
        fee_year=year,
        defaults={
            'challan_no': challan_no,
            'tuition_fee': student.monthly_fee or Decimal('0.00'),
            'transport_fee': student.transport_charges or Decimal('0.00'),
            'admission_fee': Decimal('0.00'),
            'other_charges': student.other_charges or Decimal('0.00'),
            'total_amount': total,
            'balance': total,
            'due_date': current_date + datetime.timedelta(days=10),
            'status': 'Unpaid'
        }
    )

    context = {
        "challans": [{
            "fee": fee_record,
            "student": student,
            "month_name": MONTHS_DICT[month],
        }],
        "school_name": "ACERO GRAMMAR SCHOOL",
        "school_address": "Main Campus, Education Hub, Sialkot",
        "copies": ["Bank Copy", "School Copy", "Student Copy"]
    }
    return render(request, "accounts/challan_pdf.html", context)


# ==========================================
# 5. BULK CLASS CHALLANS (ALL-IN-ONE PDF)
# ==========================================
def generate_class_challans(request):
    if request.method in ["POST", "GET"]:
        student_class = request.POST.get('student_class') or request.GET.get('class')
        fee_month = int(request.POST.get('fee_month') or request.GET.get('month') or datetime.date.today().month)
        fee_year = int(request.POST.get('fee_year') or request.GET.get('year') or datetime.date.today().year)
        due_date = datetime.date.today() + datetime.timedelta(days=10)

        students = Student.objects.filter(student_class__iexact=student_class).order_by('roll_no')
        challans_list = []

        for student in students:
            # Check admission date before issuing
            if student.enrolment_date:
                if (fee_year < student.enrolment_date.year) or (fee_year == student.enrolment_date.year and fee_month < student.enrolment_date.month):
                    continue

            challan_no = f"CH-{fee_year}{fee_month:02d}-{student.id:04d}"
            total = (student.monthly_fee or Decimal('0.00')) + (student.transport_charges or Decimal('0.00')) + (student.other_charges or Decimal('0.00'))

            fee_record, _ = StudentFee.objects.get_or_create(
                student=student,
                fee_month=fee_month,
                fee_year=fee_year,
                defaults={
                    'challan_no': challan_no,
                    'tuition_fee': student.monthly_fee or Decimal('0.00'),
                    'transport_fee': student.transport_charges or Decimal('0.00'),
                    'other_charges': student.other_charges or Decimal('0.00'),
                    'total_amount': total,
                    'balance': total,
                    'due_date': due_date,
                    'status': 'Unpaid'
                }
            )
            challans_list.append({
                "fee": fee_record,
                "student": student,
                "month_name": MONTHS_DICT[fee_month]
            })

        context = {
            "challans": challans_list,
            "school_name": "ACERO GRAMMAR SCHOOL",
            "school_address": "Main Campus, Education Hub, Sialkot",
            "copies": ["Bank Copy", "School Copy", "Student Copy"]
        }
        return render(request, "accounts/challan_pdf.html", context)

    return redirect("add_fees")
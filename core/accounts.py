import io
import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Sum
from django.contrib import messages
from .models import CoreStudent as Student, CoreStudentFee as StudentFee

# ReportLab Imports
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

MONTHS_DICT = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April',
    5: 'May', 6: 'June', 7: 'July', 8: 'August',
    9: 'September', 10: 'October', 11: 'November', 12: 'December'
}

# ==========================================
# 1. FEE RECORDS VIEW (Paid / Unpaid / All Filters)
# ==========================================
def fee_records(request):
    current_date = datetime.date.today()
    selected_month = int(request.GET.get('month', current_date.month))
    selected_year = int(request.GET.get('year', current_date.year))
    selected_class = request.GET.get('class', '').strip()
    status_filter = request.GET.get('status', 'all').strip()

    # Step 1: Filter students eligible based on enrolment_date
    students_qs = Student.objects.filter(is_active=True)
    if selected_class:
        students_qs = students_qs.filter(student_class__iexact=selected_class)

    for student in students_qs:
        if student.enrolment_date:
            enrol_year = student.enrolment_date.year
            enrol_month = student.enrolment_date.month
            if (selected_year < enrol_year) or (selected_year == enrol_year and selected_month < enrol_month):
                continue

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

    # Base fees queryset for analytics
    base_fees_qs = StudentFee.objects.select_related('student').filter(
        fee_month=selected_month,
        fee_year=selected_year,
        student__is_active=True
    ).order_by('student__student_class', 'student__roll_no')

    if selected_class:
        base_fees_qs = base_fees_qs.filter(student__student_class__iexact=selected_class)

    # Analytics
    total_generated = base_fees_qs.count()
    paid_count = base_fees_qs.filter(status='Paid').count()
    unpaid_count = base_fees_qs.filter(status__in=['Unpaid', 'Partial']).count()

    total_receivable = base_fees_qs.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
    total_collected = base_fees_qs.aggregate(Sum('paid_amount'))['paid_amount__sum'] or Decimal('0.00')
    total_advance = base_fees_qs.aggregate(Sum('advance_fee'))['advance_fee__sum'] or Decimal('0.00')
    total_pending = total_receivable - total_collected

    paid_percentage = round((paid_count / total_generated * 100)) if total_generated > 0 else 0
    unpaid_percentage = 100 - paid_percentage if total_generated > 0 else 0

    # Apply Table Filter (Paid / Unpaid / All)
    fees_qs = base_fees_qs
    if status_filter == 'paid':
        fees_qs = fees_qs.filter(status='Paid')
    elif status_filter == 'unpaid':
        fees_qs = fees_qs.filter(status__in=['Unpaid', 'Partial'])

    context = {
        "fees": fees_qs,
        "selected_month": selected_month,
        "selected_month_name": MONTHS_DICT.get(selected_month, ''),
        "selected_year": selected_year,
        "selected_class": selected_class,
        "status_filter": status_filter,
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
# 2. ADD FEES / SEARCH BY ROLL NO & CHALLAN NO
# ==========================================
def add_fees(request):
    current_date = datetime.date.today()
    search_query = request.GET.get('q', '').strip()
    selected_class = request.GET.get('class', '').strip()

    students_list = []
    if search_query or selected_class:
        raw_students = Student.objects.filter(is_active=True).order_by('student_class', 'roll_no')
        if selected_class:
            raw_students = raw_students.filter(student_class__iexact=selected_class)
        
        # Search specifically by Roll No or Challan No (or name as fallback)
        if search_query:
            # Check if query matches a Challan No format (e.g. CH-202608-0005)
            challan_match = StudentFee.objects.filter(challan_no__iexact=search_query).first()
            if challan_match:
                raw_students = raw_students.filter(id=challan_match.student_id)
            else:
                raw_students = raw_students.filter(
                    Q(roll_no__iexact=search_query) |
                    Q(name__icontains=search_query) |
                    Q(father_name__icontains=search_query)
                )

        for s in raw_students:
            fee = StudentFee.objects.filter(
                student=s, 
                fee_month=current_date.month, 
                fee_year=current_date.year
            ).first()

            if fee:
                unpaid_bal = fee.balance
                status = fee.status
                challan_code = fee.challan_no
            else:
                std_total = (s.monthly_fee or Decimal('0.00')) + (s.transport_charges or Decimal('0.00')) + (s.other_charges or Decimal('0.00'))
                unpaid_bal = std_total
                status = 'Unpaid'
                challan_code = f"CH-{current_date.year}{current_date.month:02d}-{s.id:04d}"

            students_list.append({
                'student': s,
                'challan_no': challan_code,
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
# 3. 12-MONTH STUDENT LEDGER API & PDF (ReportLab)
# ==========================================
def student_fee_ledger_api(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    current_year = datetime.date.today().year
    year = int(request.GET.get('year', current_year))

    records = StudentFee.objects.filter(student=student, fee_year=year).order_by('fee_month')
    
    ledger = []
    total_billed = Decimal('0.00')
    total_paid = Decimal('0.00')
    total_balance = Decimal('0.00')

    for r in records:
        total_billed += r.total_amount
        total_paid += (r.paid_amount + r.advance_fee)
        total_balance += r.balance

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
        'student_id': student.id,
        'student_name': student.name,
        'father_name': student.father_name,
        'student_class': student.student_class,
        'roll_no': student.roll_no,
        'year': year,
        'total_billed': str(total_billed),
        'total_paid': str(total_paid),
        'total_balance': str(total_balance),
        'ledger': ledger
    })


def download_student_ledger_pdf(request, student_id):
    """Generates a 12-Month Student Account Statement using ReportLab"""
    student = get_object_or_404(Student, id=student_id)
    year = int(request.GET.get('year', datetime.date.today().year))
    records = StudentFee.objects.filter(student=student, fee_year=year).order_by('fee_month')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
    styles = getSampleStyleSheet()
    story = []

    # Title Banner
    title_style = ParagraphStyle(
        'MainTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#2C3752'),
        alignment=1, # Center
    )
    sub_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#6B7280'),
        alignment=1,
    )

    story.append(Paragraph("<b>ACERO GRAMMAR SCHOOL</b>", title_style))
    story.append(Paragraph("12-Month Student Account Statement & Fee Ledger", sub_style))
    story.append(Spacer(1, 15))

    # Student Info Grid Table
    info_data = [
        [f"Student Name: {student.name}", f"Class: {student.student_class} (Roll #{student.roll_no})"],
        [f"Father's Name: {student.father_name}", f"Academic Year: {year}"],
        [f"Contact: {student.contact or '—'}", f"Generated On: {datetime.date.today().strftime('%d-%b-%Y')}"]
    ]
    info_table = Table(info_data, colWidths=[270, 270])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8F9FC')),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#1F2937')),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E5E7EB')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#ECEEF3')),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 15))

    # Ledger Table
    table_data = [["Month", "Total (Rs.)", "Paid (Rs.)", "Advance", "Balance", "Payment Date", "Method", "Status"]]
    
    total_billed = Decimal('0.00')
    total_paid = Decimal('0.00')
    total_balance = Decimal('0.00')

    for r in records:
        total_billed += r.total_amount
        total_paid += (r.paid_amount + r.advance_fee)
        total_balance += r.balance

        table_data.append([
            MONTHS_DICT.get(r.fee_month),
            f"{r.total_amount}",
            f"{r.paid_amount}",
            f"{r.advance_fee}",
            f"{r.balance}",
            r.payment_date.strftime('%d-%b-%Y') if r.payment_date else '—',
            r.payment_method or '—',
            r.status
        ])

    table_data.append(["TOTAL", f"{total_billed}", f"{total_paid}", "—", f"{total_balance}", "—", "—", "—"])

    ledger_table = Table(table_data, colWidths=[70, 65, 65, 55, 65, 80, 75, 65])
    ledger_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2C3752')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (1,1), (4,-1), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F3F4F6')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
    ]))
    story.append(ledger_table)
    
    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Ledger_{student.name}_{year}.pdf"'
    return response


# ==========================================
# 4. DOWNLOAD UNPAID DEFAULTERS PDF (ReportLab)
# ==========================================
def download_defaulters_pdf(request):
    """Generates Fee Defaulters List PDF for selected Month & Class"""
    month = int(request.GET.get('month', datetime.date.today().month))
    year = int(request.GET.get('year', datetime.date.today().year))
    selected_class = request.GET.get('class', '').strip()

    fees = StudentFee.objects.select_related('student').filter(
        fee_month=month,
        fee_year=year,
        status__in=['Unpaid', 'Partial'],
        student__is_active=True
    ).order_by('student__student_class', 'student__roll_no')

    if selected_class:
        fees = fees.filter(student__student_class__iexact=selected_class)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('DTitle', parent=styles['Heading1'], fontSize=17, alignment=1, textColor=colors.HexColor('#E15C5C'))
    sub_style = ParagraphStyle('DSub', parent=styles['Normal'], fontSize=10, alignment=1, textColor=colors.HexColor('#4B5563'))

    class_header = f"Class: {selected_class}" if selected_class else "Entire School (All Classes)"
    story.append(Paragraph("<b>ACERO GRAMMAR SCHOOL</b>", title_style))
    story.append(Paragraph(f"<b>Fee Defaulters List — {MONTHS_DICT.get(month)} {year}</b> ({class_header})", sub_style))
    story.append(Spacer(1, 15))

    table_data = [["Sr.", "Student Name", "Father's Name", "Class", "Roll #", "Contact", "Due Amount (Rs.)"]]
    
    total_unpaid = Decimal('0.00')
    for idx, f in enumerate(fees, start=1):
        total_unpaid += f.balance
        table_data.append([
            str(idx),
            f.student.name,
            f.student.father_name,
            f.student.student_class,
            f.student.roll_no,
            f.student.contact or '—',
            f"Rs. {f.balance}"
        ])

    table_data.append(["TOTAL", f"{len(fees)} Defaulters", "", "", "", "", f"Rs. {total_unpaid}"])

    table = Table(table_data, colWidths=[30, 110, 110, 55, 50, 95, 90])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E15C5C')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (1,1), (2,-1), 'LEFT'),
        ('ALIGN', (-1,1), (-1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FDECEC')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Defaulters_{MONTHS_DICT.get(month)}_{year}.pdf"'
    return response


# ==========================================
# 5. SINGLE & BULK CHALLANS VIEW
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


def generate_class_challans(request):
    if request.method in ["POST", "GET"]:
        student_class = request.POST.get('student_class') or request.GET.get('class')
        fee_month = int(request.POST.get('fee_month') or request.GET.get('month') or datetime.date.today().month)
        fee_year = int(request.POST.get('fee_year') or request.GET.get('year') or datetime.date.today().year)
        due_date = datetime.date.today() + datetime.timedelta(days=10)

        students = Student.objects.filter(student_class__iexact=student_class, is_active=True).order_by('roll_no')
        challans_list = []

        for student in students:
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

def update_fee_record(request, fee_id):
    fee_record = get_object_or_404(StudentFee, id=fee_id)
    if request.method == "POST":
        fee_record.tuition_fee = Decimal(request.POST.get('tuition_fee', '0.00'))
        fee_record.transport_fee = Decimal(request.POST.get('transport_fee', '0.00'))
        fee_record.other_charges = Decimal(request.POST.get('other_charges', '0.00'))
        fee_record.fine = Decimal(request.POST.get('fine', '0.00'))
        fee_record.paid_amount = Decimal(request.POST.get('paid_amount', '0.00'))
        fee_record.advance_fee = Decimal(request.POST.get('advance_fee', '0.00'))
        
        # Calculate Total and Balance
        fee_record.total_amount = fee_record.tuition_fee + fee_record.transport_fee + fee_record.other_charges + fee_record.fine + fee_record.arrears
        fee_record.balance = max(Decimal('0.00'), fee_record.total_amount - (fee_record.paid_amount + fee_record.advance_fee))
        
        if fee_record.balance == Decimal('0.00'):
            fee_record.status = 'Paid'
        elif fee_record.paid_amount > Decimal('0.00'):
            fee_record.status = 'Partial'
        else:
            fee_record.status = 'Unpaid'

        fee_record.payment_date = request.POST.get('payment_date') or None
        fee_record.payment_method = request.POST.get('payment_method') or None
        fee_record.notes = request.POST.get('notes') or None
        fee_record.save()

        messages.success(request, f"Fee record {fee_record.challan_no} updated successfully!")
        
        # Redirect back to same month & year
        return redirect(f"/accounts/fees/?month={fee_record.fee_month}&year={fee_record.fee_year}")
    
    return redirect("fee_records")
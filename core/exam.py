from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import time
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.db import IntegrityError, connection
from django.http import JsonResponse, HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

import json
from datetime import datetime, timedelta

from .models import CoreStudent, CoreTeacher, CoreExam, CoreExamMark
from .user_rights import get_user_module_permissions

SHIFT1_START = time(8, 0)
SHIFT1_END   = time(14, 0)
SHIFT2_START = time(14, 0)
SHIFT2_END   = time(17, 0)


def fits_in_one_shift(start_t, end_t):
    in_shift1 = (start_t >= SHIFT1_START and end_t <= SHIFT1_END)
    in_shift2 = (start_t >= SHIFT2_START and end_t <= SHIFT2_END)
    return in_shift1 or in_shift2


# ══════════════════════════════════════════════════
#  CLASS + SECTION HELPERS
# ══════════════════════════════════════════════════

def get_class_sections():
    cmap = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT [class], section FROM Class_defination ORDER BY [class], section")
            for cls, sec in cursor.fetchall():
                c = (cls or "").strip()
                s = (sec or "").strip() or "A"
                if not c:
                    continue
                cmap.setdefault(c, set()).add(s)
    except Exception as e:
        print("WARNING - Class_defination read error:", e)
    return {k: sorted(v) for k, v in sorted(cmap.items())}


def get_subjects():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT subject_name, subject_type FROM Subject_Defination ORDER BY subject_name")
            return [{"subject_name": r[0], "subject_type": r[1] or ""} for r in cursor.fetchall()]
    except Exception as e:
        print("WARNING - Subject_Defination read error:", e)
        return []


def valid_class_section(cls, sec):
    m = get_class_sections()
    return cls in m and sec in m[cls]


def students_of(cls, sec):
    qs = CoreStudent.objects.filter(student_class=cls)
    if sec:
        exact = qs.filter(section__iexact=sec)
        if exact.exists():
            return exact.order_by("roll_no")
        if sec.upper() == "A":
            blank = qs.filter(Q(section__isnull=True) | Q(section=""))
            if blank.exists():
                return blank.order_by("roll_no")
        return CoreStudent.objects.none()
    return qs.order_by("roll_no")


# ══════════════════════════════════════════════════

def exam_dashboard(request):
    perms = get_user_module_permissions(request.user, "exam")
    if not perms.get('can_view'):
        messages.error(request, "Access Denied: You do not have permission to view Exams.")
        return redirect('dashboard')
    return render(request, "exam/exam_dashboard.html", {'perms': perms})


def exam_list(request):
    # ================= RIGHTS CHECK: VIEW =================
    perms = get_user_module_permissions(request.user, "exam")
    if not perms.get('can_view'):
        messages.error(request, "Access Denied: You do not have permission to view Examinations.")
        # ✅ Referer check taake teacher/student apne hi page par rahe
        role = request.session.get('user_role')
        fallback = 'teacher_dashboard' if role == 'Teacher' else ('student_dashboard' if role == 'Student' else 'dashboard')
        return redirect(request.META.get('HTTP_REFERER') or fallback)

    class_sections = get_class_sections()
    teachers = CoreTeacher.objects.all().order_by("name")
    exams = CoreExam.objects.select_related("teacher").all().order_by("-id")[:30]

    return render(request, "exam/exam_list.html", {
        "class_sections": class_sections,
        "class_sections_json": json.dumps(class_sections),
        "subjects": get_subjects(),
        "teachers": teachers,
        "exams": exams,
        "perms": perms,
    })


def exam_create(request):
    perms = get_user_module_permissions(request.user, "exam")
    if not perms.get('can_add'):
        messages.error(request, "Access Denied: You do not have permission to schedule new exams.")
        return redirect("exam_list")

    if request.method != "POST":
        return redirect("exam_list")

    student_class = (request.POST.get("class") or "").strip()
    section       = (request.POST.get("section") or "").strip()
    term          = (request.POST.get("term") or "1st").strip()
    subject       = (request.POST.get("subject") or "").strip()
    total_marks   = request.POST.get("total_marks") or "100"
    passing_marks = request.POST.get("passing_marks") or None
    teacher_id    = request.POST.get("teacher") or ""
    exam_date     = request.POST.get("exam_date") or None
    start_time    = request.POST.get("start_time") or None
    end_time      = request.POST.get("end_time") or None

    if not student_class or not section or not subject or not exam_date or not start_time or not end_time:
        messages.error(request, "Class, Section, Subject, Date, Start Time and End Time are required.")
        return redirect("exam_list")

    if not valid_class_section(student_class, section):
        messages.error(request, f"Invalid class-section combination: {student_class} - {section}")
        return redirect("exam_list")

    if not teacher_id:
        messages.error(request, "Teacher is required for exam scheduling.")
        return redirect("exam_list")

    try:
        exam_date_obj = datetime.strptime(exam_date, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Invalid exam date format.")
        return redirect("exam_list")

    today = timezone.localdate()
    if exam_date_obj < today:
        messages.error(request, "You cannot create an exam for a past date.")
        return redirect("exam_list")

    try:
        start_t = datetime.strptime(start_time, "%H:%M").time()
        end_t   = datetime.strptime(end_time, "%H:%M").time()
    except ValueError:
        messages.error(request, "Invalid start or end time format.")
        return redirect("exam_list")

    if start_t >= end_t:
        messages.error(request, "End Time must be greater than Start Time.")
        return redirect("exam_list")

    teacher = CoreTeacher.objects.filter(id=teacher_id).first()
    if not teacher:
        messages.error(request, "Invalid teacher selected.")
        return redirect("exam_list")

    try:
        total_marks_int = int(total_marks)
        passing_marks_val = float(passing_marks) if passing_marks else round(total_marks_int * 0.50, 2)
    except ValueError:
        total_marks_int = 100
        passing_marks_val = 50.0

    if not fits_in_one_shift(start_t, end_t):
        messages.error(request, "Exam time must be within Shift 1 (08:00–14:00) or Shift 2 (14:00–17:00).")
        return redirect("exam_list")

    dt1 = datetime.combine(datetime.today(), start_t)
    dt2 = datetime.combine(datetime.today(), end_t)
    if (dt2 - dt1) > timedelta(hours=3):
        messages.error(request, "Exam duration cannot be more than 3 hours.")
        return redirect("exam_list")

    conflict = CoreExam.objects.filter(
        student_class=student_class,
        section=section,
        teacher_id=teacher.id,
        subject__iexact=subject,
        exam_date=exam_date_obj,
    ).filter(
        start_time__lt=end_t,
        end_time__gt=start_t
    ).exists()

    if conflict:
        messages.error(request, "Conflict: Same class-section, subject & teacher already scheduled in this time range.")
        return redirect("exam_list")

    teacher_busy = CoreExam.objects.filter(
        teacher_id=teacher.id,
        exam_date=exam_date_obj,
    ).filter(
        start_time__lt=end_t,
        end_time__gt=start_t
    ).exclude(
        student_class=student_class, section=section
    ).first()

    if teacher_busy:
        messages.error(
            request,
            f"Conflict: {teacher.name} is already assigned to "
            f"{teacher_busy.student_class}-{teacher_busy.section} ({teacher_busy.subject}) at this time."
        )
        return redirect("exam_list")

    try:
        exam = CoreExam.objects.create(
            student_class=student_class,
            section=section,
            term=term,
            subject=subject,
            total_marks=total_marks_int,
            passing_marks=passing_marks_val,
            teacher=teacher,
            exam_date=exam_date_obj,
            start_time=start_t,
            end_time=end_t,
            created_at=timezone.now(),
        )
    except IntegrityError:
        messages.error(request, "Duplicate schedule not allowed.")
        return redirect("exam_list")

    students = students_of(student_class, section)
    CoreExamMark.objects.bulk_create([
        CoreExamMark(exam=exam, student=s, obtained_marks=0) for s in students
    ])

    if not students.exists():
        messages.warning(request, f"Exam created but no students found in {student_class} - {section}.")
    else:
        messages.success(request, f"Exam created: {student_class}-{section} — {term} — {subject} ({students.count()} students)")

    return redirect("exam_marks", exam_id=exam.id)


def exam_marks_pdf(request, exam_id):
    perms = get_user_module_permissions(request.user, "exam")
    if not perms.get('can_print'):
        messages.error(request, "Access Denied: You do not have permission to download marks PDF.")
        return redirect("exam_list")

    exam = get_object_or_404(CoreExam, id=exam_id)
    marks_qs = CoreExamMark.objects.select_related("student").filter(exam=exam).order_by("student__roll_no")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="exam_{exam.id}_marks.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4, leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24)
    styles = getSampleStyleSheet()
    story = []

    title = f"Marks Sheet — {exam.student_class}-{exam.section or '—'} | {exam.term} | {exam.subject}"
    teacher_name = exam.teacher.name if exam.teacher else "—"
    date_txt = exam.exam_date.strftime("%Y-%m-%d") if exam.exam_date else "—"
    time_txt = f"{exam.start_time.strftime('%H:%M') if exam.start_time else '—'} - {exam.end_time.strftime('%H:%M') if exam.end_time else '—'}"
    total_txt = str(exam.total_marks) if exam.total_marks is not None else "—"
    subtitle = f"Teacher: {teacher_name}   Date: {date_txt}   Time: {time_txt}   Total Marks: {total_txt}"

    story.append(Paragraph(title, styles["Title"]))
    story.append(Paragraph(subtitle, styles["Normal"]))
    story.append(Spacer(1, 12))

    data = [["#", "Student", "Roll No", "Obtained", "Grade", "Remarks"]]
    i = 1
    for m in marks_qs:
        obtained = m.obtained_marks
        obtained_val = float(obtained) if obtained is not None else 0.0
        obtained_txt = f"{obtained_val:.2f}"
        g, r = grade_and_remarks(obtained_val, exam.total_marks or 0, exam.passing_marks)
        data.append([str(i), m.student.name, str(m.student.roll_no), obtained_txt, g, r])
        i += 1

    table = Table(data, colWidths=[26, 180, 70, 70, 50, 120])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#f3f4f6")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (-1, 1), (-1, -1), "CENTER"),
    ]))
    story.append(table)
    doc.build(story)
    return response


def grade_and_remarks(obtained, total, passing_marks=None):
    if total in (None, 0) or obtained is None:
        return ("—", "—")

    obtained = float(obtained)
    total = float(total)

    if passing_marks is None:
        passing_marks = round(total * 0.50, 2)
    passing_marks = float(passing_marks)

    if obtained < passing_marks:
        return ("F", "Fail")

    pct = (obtained / total) * 100 if total > 0 else 0
    if pct >= 80: return ("A+", "Pass")
    if pct >= 70: return ("A", "Pass")
    if pct >= 60: return ("B", "Pass")
    if pct >= 50: return ("C", "Pass")
    return ("D", "Pass")


def exam_marks(request, exam_id):
    perms = get_user_module_permissions(request.user, "exam")
    if not perms.get('can_view'):
        messages.error(request, "Access Denied: You do not have permission to view marks entry.")
        return redirect("exam_list")

    exam = get_object_or_404(CoreExam, id=exam_id)
    marks_qs = CoreExamMark.objects.select_related("student").filter(exam=exam).order_by("student__roll_no")

    if request.method == "POST":
        if not perms.get('can_edit') and not perms.get('can_add'):
            messages.error(request, "Access Denied: You do not have permission to enter or edit marks.")
            return redirect("exam_marks", exam_id=exam.id)

        errors = 0
        for m in marks_qs:
            val = request.POST.get(f"marks_{m.student_id}", "").strip()
            if val == "":
                continue
            try:
                obtained = float(val)
            except ValueError:
                errors += 1
                continue

            if obtained < 0:
                obtained = 0
            if exam.total_marks and obtained > exam.total_marks:
                obtained = exam.total_marks

            m.obtained_marks = obtained
            m.save()

        messages.success(request, "Marks saved successfully!" if errors == 0 else f"Saved with {errors} invalid mark(s).")
        return redirect("exam_marks", exam_id=exam.id)

    total = float(exam.total_marks or 100)
    passing = float(exam.passing_marks) if getattr(exam, "passing_marks", None) is not None else round(total * 0.50, 2)

    for m in marks_qs:
        obtained_val = float(m.obtained_marks or 0)
        grade, remarks = grade_and_remarks(obtained_val, total, passing)
        m.calc_grade = grade
        m.calc_remarks = remarks

    return render(request, "exam/exam_marks.html", {"exam": exam, "marks": marks_qs, "perms": perms})


def exam_edit(request, exam_id):
    perms = get_user_module_permissions(request.user, "exam")
    if not perms.get('can_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit exams.")
        return redirect("exam_list")

    exam = get_object_or_404(CoreExam, id=exam_id)
    teachers = CoreTeacher.objects.all().order_by("name")
    class_sections = get_class_sections()

    if request.method == "POST":
        student_class = (request.POST.get("class") or "").strip()
        section       = (request.POST.get("section") or "").strip()
        term          = (request.POST.get("term") or "1st").strip()
        subject       = (request.POST.get("subject") or "").strip()
        total_marks   = request.POST.get("total_marks") or "100"
        teacher_id    = request.POST.get("teacher") or ""
        passing_marks = request.POST.get("passing_marks") or None
        exam_date     = request.POST.get("exam_date") or None
        start_time    = request.POST.get("start_time") or None
        end_time      = request.POST.get("end_time") or None

        if not student_class or not section or not subject or not exam_date or not start_time or not end_time:
            messages.error(request, "Class, Section, Subject, Date, Start Time and End Time are required.")
            return redirect("exam_edit", exam_id=exam.id)

        if not valid_class_section(student_class, section):
            messages.error(request, f"Invalid class-section combination: {student_class} - {section}")
            return redirect("exam_edit", exam_id=exam.id)

        if not teacher_id:
            messages.error(request, "Teacher is required for exam scheduling.")
            return redirect("exam_edit", exam_id=exam.id)

        teacher = CoreTeacher.objects.filter(id=teacher_id).first()
        if not teacher:
            messages.error(request, "Invalid teacher selected.")
            return redirect("exam_edit", exam_id=exam.id)

        try:
            total_marks_int = int(total_marks)
        except ValueError:
            total_marks_int = 100

        try:
            passing_marks_val = float(passing_marks) if passing_marks else round(total_marks_int * 0.50, 2)
        except ValueError:
            passing_marks_val = round(total_marks_int * 0.50, 2)

        try:
            start_t = datetime.strptime(start_time, "%H:%M").time()
            end_t   = datetime.strptime(end_time, "%H:%M").time()
        except ValueError:
            messages.error(request, "Invalid time format.")
            return redirect("exam_edit", exam_id=exam.id)

        if start_t >= end_t:
            messages.error(request, "End Time must be greater than Start Time.")
            return redirect("exam_edit", exam_id=exam.id)
        if not fits_in_one_shift(start_t, end_t):
            messages.error(request, "Exam time must be within Shift 1 (08:00–14:00) or Shift 2 (14:00–17:00).")
            return redirect("exam_edit", exam_id=exam.id)

        dt1 = datetime.combine(datetime.today(), start_t)
        dt2 = datetime.combine(datetime.today(), end_t)
        if (dt2 - dt1) > timedelta(hours=3):
            messages.error(request, "Exam duration cannot be more than 3 hours.")
            return redirect("exam_edit", exam_id=exam.id)

        conflict = CoreExam.objects.filter(
            student_class=student_class,
            section=section,
            teacher_id=teacher.id,
            subject__iexact=subject,
            exam_date=exam_date,
        ).filter(start_time__lt=end_t, end_time__gt=start_t).exclude(id=exam.id).exists()

        if conflict:
            messages.error(request, "Conflict: Same class-section, subject & teacher already scheduled in this time range.")
            return redirect("exam_edit", exam_id=exam.id)

        old_class = exam.student_class
        old_section = exam.section

        try:
            exam_date_obj = datetime.strptime(exam_date, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid exam date.")
            return redirect("exam_edit", exam_id=exam.id)

        today = timezone.localdate()
        if exam_date_obj < today:
            messages.error(request, "You cannot set an exam date in the past.")
            return redirect("exam_edit", exam_id=exam.id)

        exam.student_class = student_class
        exam.section       = section
        exam.term          = term
        exam.subject       = subject
        exam.total_marks   = total_marks_int
        exam.passing_marks = passing_marks_val
        exam.teacher       = teacher
        exam.exam_date     = exam_date_obj
        exam.start_time    = start_t
        exam.end_time      = end_t

        try:
            exam.save()
        except IntegrityError:
            messages.error(request, "Duplicate schedule not allowed.")
            return redirect("exam_edit", exam_id=exam.id)

        if old_class != student_class or old_section != section:
            CoreExamMark.objects.filter(exam_id=exam.id).delete()
            students = students_of(student_class, section)
            CoreExamMark.objects.bulk_create([
                CoreExamMark(exam=exam, student=s, obtained_marks=0) for s in students
            ])
            messages.success(request, f"Exam updated. Class/Section changed — marks list rebuilt ({students.count()} students).")
        else:
            messages.success(request, "Exam updated successfully.")
        return redirect("exam_list")

    return render(request, "exam/exam_edit.html", {
        "exam": exam,
        "class_sections": class_sections,
        "class_sections_json": json.dumps(class_sections),
        "subjects": get_subjects(),
        "teachers": teachers,
        "perms": perms,
    })


def exam_list_pdf(request):
    perms = get_user_module_permissions(request.user, "exam")
    if not perms.get('can_print'):
        messages.error(request, "Access Denied: You do not have permission to download exam schedule.")
        return redirect("exam_list")

    q = (request.GET.get("q") or "").strip()
    cls = (request.GET.get("class") or "").strip()
    sec = (request.GET.get("section") or "").strip()
    date_str = (request.GET.get("date") or "").strip()

    exams = CoreExam.objects.select_related("teacher").all().order_by("-id")
    if cls: exams = exams.filter(student_class=cls)
    if sec: exams = exams.filter(section__iexact=sec)
    if date_str: exams = exams.filter(exam_date=date_str)
    if q:
        parsed_time = None
        try: parsed_time = datetime.strptime(q, "%H:%M").time()
        except ValueError: pass
        if parsed_time:
            exams = exams.filter(start_time__lte=parsed_time, end_time__gte=parsed_time)
        else:
            exams = exams.filter(
                Q(subject__icontains=q) | Q(term__icontains=q) |
                Q(student_class__icontains=q) | Q(section__icontains=q) |
                Q(teacher__name__icontains=q)
            )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="exam_list.pdf"'
    doc = SimpleDocTemplate(response, pagesize=A4, leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Exam Schedule List", styles["Title"]))
    story.append(Paragraph(
        f"Class: {cls or 'All'}   Section: {sec or 'All'}   Search: {q or '—'}",
        styles["Normal"]
    ))
    story.append(Spacer(1, 12))

    data = [["#", "Class", "Sec", "Term", "Subject", "Teacher", "Date", "Time"]]
    i = 1
    for e in exams[:200]:
        teacher_name = e.teacher.name if e.teacher else "—"
        date_txt = e.exam_date.strftime("%Y-%m-%d") if e.exam_date else "—"
        time_txt = f"{e.start_time.strftime('%H:%M') if e.start_time else '—'} - {e.end_time.strftime('%H:%M') if e.end_time else '—'}"
        data.append([str(i), e.student_class, e.section or "—", e.term, e.subject, teacher_name, date_txt, time_txt])
        i += 1

    table = Table(data, colWidths=[20, 50, 30, 38, 130, 85, 62, 78])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#f3f4f6")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 1), (2, -1), "CENTER"),
    ]))
    story.append(table)
    doc.build(story)
    return response


@require_POST
def exam_delete(request, exam_id):
    perms = get_user_module_permissions(request.user, "exam")
    if not perms.get('can_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete exams.")
        return redirect("exam_list")

    exam = get_object_or_404(CoreExam, id=exam_id)
    CoreExamMark.objects.filter(exam_id=exam.id).delete()
    exam.delete()
    messages.success(request, "Exam deleted successfully.")
    return redirect("exam_list")


def exam_list_api(request):
    perms = get_user_module_permissions(request.user, "exam")
    if not perms.get('can_view'):
        return JsonResponse({"results": []}, status=403)

    q    = (request.GET.get("q") or "").strip()
    cls  = (request.GET.get("class") or "").strip()
    sec  = (request.GET.get("section") or "").strip()
    term = (request.GET.get("term") or "").strip()
    year = (request.GET.get("year") or "").strip()

    exams = CoreExam.objects.select_related("teacher").all().order_by("-id")

    if cls: exams = exams.filter(student_class=cls)
    if sec: exams = exams.filter(section__iexact=sec)
    if term: exams = exams.filter(term=term)
    if year: exams = exams.filter(exam_date__year=year)

    if q:
        parsed_time = None
        try:
            parsed_time = datetime.strptime(q, "%H:%M").time()
        except ValueError:
            pass

        if parsed_time:
            exams = exams.filter(start_time__lte=parsed_time, end_time__gte=parsed_time)
        else:
            exams = exams.filter(
                Q(subject__icontains=q) |
                Q(term__icontains=q) |
                Q(student_class__icontains=q) |
                Q(section__icontains=q) |
                Q(teacher__name__icontains=q)
            )

    exams = exams[:50]
    data = []
    for e in exams:
        total = float(e.total_marks or 100)
        passing_marks = float(e.passing_marks) if getattr(e, 'passing_marks', None) else round(total * 0.50, 2)

        data.append({
            "id": e.id,
            "student_class": e.student_class,
            "section": e.section or "",
            "term": e.term,
            "subject": e.subject,
            "teacher": e.teacher.name if e.teacher else "—",
            "exam_date": e.exam_date.isoformat() if e.exam_date else "",
            "start_time": e.start_time.strftime("%H:%M") if e.start_time else "",
            "end_time": e.end_time.strftime("%H:%M") if e.end_time else "",
            "total_marks": total,
            "passing_marks": passing_marks,
        })
    return JsonResponse({"results": data})


def exam_list_pdf_view(request):
    perms = get_user_module_permissions(request.user, "exam")
    if not perms.get('can_print'):
        messages.error(request, "Access Denied: You do not have permission to view schedule PDF.")
        return redirect("exam_list")

    cls  = (request.GET.get("class") or "").strip()
    sec  = (request.GET.get("section") or "").strip()
    term = (request.GET.get("term") or "").strip()
    year = (request.GET.get("year") or "").strip()
    q    = (request.GET.get("q") or "").strip()
    custom_passing = (request.GET.get("passing_marks") or "").strip()

    exams = CoreExam.objects.select_related("teacher").all().order_by("-id")
    if cls:  exams = exams.filter(student_class=cls)
    if sec:  exams = exams.filter(section__iexact=sec)
    if term: exams = exams.filter(term=term)
    if year: exams = exams.filter(exam_date__year=year)

    for e in exams:
        tot = float(e.total_marks or 100)
        e.calc_passing = float(custom_passing) if custom_passing else round(tot * 0.50, 2)

    return render(request, "exam/exam_list_pdf.html", {
        "exams": exams,
        "selected_class": cls,
        "selected_section": sec,
        "selected_term": term,
        "selected_year": year,
        "custom_passing_marks": custom_passing or "50% (Default)",
    })
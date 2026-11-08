from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum
from django.db import connection
from django.utils import timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from .models import CoreStudent, CoreExam, CoreExamMark, StudentResultRemark
from xml.sax.saxutils import escape 
from .context_processors import get_school_profile
from .user_rights import get_user_module_permissions

TERM_CHOICES = [("1st", "1st Term"), ("2nd", "2nd Term"), ("3rd", "3rd Term")]

def school_header(story, color="#111827", title=None):
    """PDF letterhead — school details DB se."""
    school = get_school_profile()
    accent = colors.HexColor(color)

    name_style = ParagraphStyle(
        "SchoolName",
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        alignment=1,
        textColor=accent,
        spaceAfter=4,
    )
    line_style = ParagraphStyle(
        "SchoolLine",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        alignment=1,
        textColor=colors.HexColor("#6B7280"),
    )

    story.append(Paragraph(escape((school.get("school_name") or "School").upper()), name_style))

    loc = ", ".join(filter(None, [school.get("campus_name"), school.get("address")]))
    if loc:
        story.append(Paragraph(escape(loc), line_style))

    contact = "   |   ".join(filter(None, [
        f"Ph: {school['phone_number']}" if school.get("phone_number") else "",
        school.get("email") or "",
    ]))
    
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=2, color=accent, spaceBefore=0, spaceAfter=10))

    if title:
        badge = Table([[title]], hAlign="CENTER")
        badge.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), accent),
            ("TEXTCOLOR",     (0,0), (-1,-1), colors.white),
            ("FONTNAME",      (0,0), (-1,-1), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 10),
            ("ALIGN",         (0,0), (-1,-1), "CENTER"),
            ("LEFTPADDING",   (0,0), (-1,-1), 18),
            ("RIGHTPADDING",  (0,0), (-1,-1), 18),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ]))
        story.append(badge)
        story.append(Spacer(1, 12))
            

def grade_of(pct):
    if pct >= 90: return "A+"
    if pct >= 80: return "A"
    if pct >= 70: return "B"
    if pct >= 60: return "C"
    if pct >= 50: return "D"
    return "F"


def performance_label(pct):
    if pct >= 90: return "Outstanding"
    if pct >= 80: return "Excellent"
    if pct >= 70: return "Very Good"
    if pct >= 60: return "Good"
    if pct >= 50: return "Satisfactory"
    return "Needs Improvement"


def term_exams(cls, term):
    return CoreExam.objects.filter(student_class=cls, term=term).order_by("subject")


def class_term_summary(cls, term):
    exams = term_exams(cls, term)
    total_term_marks = float(exams.aggregate(t=Sum("total_marks"))["t"] or 0)

    agg = (CoreExamMark.objects
           .filter(exam__in=exams)
           .values("student_id")
           .annotate(total=Sum("obtained_marks")))

    obtained_map = {a["student_id"]: float(a["total"] or 0) for a in agg}

    students = CoreStudent.objects.filter(student_class=cls)
    rows = []
    for s in students:
        obt = obtained_map.get(s.id, 0.0)
        pct = (obt / total_term_marks * 100) if total_term_marks else 0.0
        rows.append({"id": s.id, "obtained": obt, "pct": pct})

    rows.sort(key=lambda r: r["obtained"], reverse=True)

    per_student = {}
    last_val, last_rank = None, 0
    for idx, r in enumerate(rows, start=1):
        if last_val is None or r["obtained"] != last_val:
            last_rank = idx
            last_val = r["obtained"]
        per_student[r["id"]] = {"obtained": r["obtained"], "pct": r["pct"], "rank": last_rank}

    return total_term_marks, per_student


def results_list(request):
    # ================= RIGHTS CHECK: VIEW =================
    perms = get_user_module_permissions(request.user, "results")
    if not perms.get('can_view'):
        messages.error(request, "Access Denied: You do not have permission to view Results.")
        return redirect('dashboard')

    with connection.cursor() as cursor:
        cursor.execute("SELECT [class], section FROM Class_defination ORDER BY [class]")
        classes = [{"class_field": row[0], "section": row[1] or ""} for row in cursor.fetchall()]
        
    return render(request, "results/results_list.html", {
        "classes": classes, 
        "terms": TERM_CHOICES,
        "perms": perms,
    })


def results_students_api(request):
    perms = get_user_module_permissions(request.user, "results")
    if not perms.get('can_view'):
        return JsonResponse({"results": []}, status=403)

    cls = (request.GET.get("class") or "").strip()
    term = (request.GET.get("term") or "").strip()

    if not cls or not term:
        return JsonResponse({"results": []})

    total_term_marks, per_student = class_term_summary(cls, term)
    students = CoreStudent.objects.filter(student_class=cls).order_by("roll_no")

    remarks_map = {
        r.student_id: (r.remarks or "")
        for r in StudentResultRemark.objects.filter(student_class=cls, term=term)
    }

    data = []
    for s in students:
        info = per_student.get(s.id, {"obtained": 0.0, "pct": 0.0, "rank": 0})
        pct = round(info["pct"], 2)
        data.append({
            "id": s.id,
            "name": s.name,
            "roll_no": s.roll_no,
            "percentage": pct,
            "grade": grade_of(pct),
            "position": info["rank"],
            "remark": remarks_map.get(s.id) or performance_label(pct),
        })

    return JsonResponse({"results": data})


def student_result(request, student_id):
    # ================= RIGHTS CHECK: VIEW =================
    perms = get_user_module_permissions(request.user, "results")
    if not perms.get('can_view'):
        messages.error(request, "Access Denied: You do not have permission to view Student Results.")
        return redirect('dashboard')

    student = get_object_or_404(CoreStudent, id=student_id)
    cls = (request.GET.get("class") or request.POST.get("class") or student.student_class).strip()
    term = (request.GET.get("term") or request.POST.get("term") or "1st").strip()

    # Save teacher remarks
    if request.method == "POST":
        # ================= RIGHTS CHECK: EDIT/ADD =================
        if not perms.get('can_edit') and not perms.get('can_add'):
            messages.error(request, "Access Denied: You do not have permission to write or edit remarks.")
            return redirect(f"/results/{student.id}/?class={cls}&term={term}")

        text = (request.POST.get("remarks") or "").strip()

        obj = StudentResultRemark.objects.filter(student_id=student.id, student_class=cls, term=term).first()
        if obj:
            obj.remarks = text
            obj.updated_at = timezone.now()
            obj.save()
        else:
            StudentResultRemark.objects.create(
                student_id=student.id,
                student_class=cls,
                term=term,
                remarks=text,
                updated_at=timezone.now(),
            )

        messages.success(request, "Remarks saved successfully.")
        return redirect(f"/results/{student.id}/?class={cls}&term={term}")

    exams = term_exams(cls, term)
    marks = CoreExamMark.objects.select_related("exam").filter(student_id=student.id, exam__in=exams)
    mark_map = {m.exam_id: m for m in marks}

    rows = []
    total_obtained = 0.0
    total_marks = 0.0

    for e in exams:
        m = mark_map.get(e.id)
        obt = float(m.obtained_marks) if (m and m.obtained_marks is not None) else 0.0
        tot = float(e.total_marks or 0)
        pct = (obt / tot * 100) if tot else 0.0

        rows.append({
            "subject": e.subject,
            "obtained": round(obt, 2),
            "total": round(tot, 2),
            "percentage": round(pct, 2),
            "grade": grade_of(pct),
            "status": "Pass" if pct >= 50 else "Fail",
        })

        total_obtained += obt
        total_marks += tot

    overall_pct = (total_obtained / total_marks * 100) if total_marks else 0.0

    _, per_student = class_term_summary(cls, term)
    rank = per_student.get(student.id, {}).get("rank", 0)
    strength = len(per_student)

    remark_obj = StudentResultRemark.objects.filter(student_id=student.id, student_class=cls, term=term).first()

    return render(request, "results/student_result.html", {
        "student": student,
        "student_class": cls,
        "term": term,
        "terms": TERM_CHOICES,
        "rows": rows,
        "total_obtained": round(total_obtained, 2),
        "total_marks": round(total_marks, 2),
        "overall_pct": round(overall_pct, 2),
        "overall_grade": grade_of(overall_pct),
        "auto_label": performance_label(overall_pct),
        "position": rank,
        "class_strength": strength,
        "teacher_remarks": remark_obj.remarks if remark_obj else "",
        "result_status": "PASS" if overall_pct >= 50 else "FAIL",
        "perms": perms,
    })


def student_result_chart_api(request, student_id):
    perms = get_user_module_permissions(request.user, "results")
    if not perms.get('can_view'):
        return JsonResponse({"labels": [], "percentages": []}, status=403)

    student = get_object_or_404(CoreStudent, id=student_id)
    cls = (request.GET.get("class") or student.student_class).strip()
    term = (request.GET.get("term") or "1st").strip()

    exams = term_exams(cls, term)
    marks = CoreExamMark.objects.filter(student_id=student.id, exam__in=exams)
    mark_map = {m.exam_id: m for m in marks}

    labels, pcts = [], []
    for e in exams:
        m = mark_map.get(e.id)
        obt = float(m.obtained_marks) if (m and m.obtained_marks is not None) else 0.0
        tot = float(e.total_marks or 0)
        pct = (obt / tot * 100) if tot else 0.0
        labels.append(e.subject[:8])
        pcts.append(round(pct, 1))

    return JsonResponse({"labels": labels, "percentages": pcts})


def student_result_pdf(request, student_id):
    # ================= RIGHTS CHECK: PRINT =================
    perms = get_user_module_permissions(request.user, "results")
    if not perms.get('can_print'):
        messages.error(request, "Access Denied: You do not have permission to download result cards.")
        return redirect('results_list')

    student = get_object_or_404(CoreStudent, id=student_id)
    cls = (request.GET.get("class") or student.student_class).strip()
    term = (request.GET.get("term") or "1st").strip()

    exams = term_exams(cls, term)
    marks = CoreExamMark.objects.filter(student_id=student.id, exam__in=exams)
    mark_map = {m.exam_id: m for m in marks}

    rows = []
    total_obtained = 0.0
    total_marks = 0.0

    for e in exams:
        m = mark_map.get(e.id)
        obt = float(m.obtained_marks) if (m and m.obtained_marks is not None) else 0.0
        tot = float(e.total_marks or 0)
        pct = (obt / tot * 100) if tot else 0.0

        rows.append([e.subject, f"{tot:.0f}", f"{obt:.2f}", f"{pct:.1f}%", grade_of(pct), "Pass" if pct >= 50 else "Fail"])

        total_obtained += obt
        total_marks += tot

    overall_pct = (total_obtained / total_marks * 100) if total_marks else 0.0
    _, per_student = class_term_summary(cls, term)
    rank = per_student.get(student.id, {}).get("rank", 0)
    strength = len(per_student)

    remark_obj = StudentResultRemark.objects.filter(student_id=student.id, student_class=cls, term=term).first()
    teacher_remarks = (remark_obj.remarks if remark_obj else "") or performance_label(overall_pct)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="result_{student.roll_no}_{term}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    small = ParagraphStyle("sm", parent=styles["Normal"], fontSize=9)

    story = []
    school_header(story, "#111827", title=f"Progress Report Card — {term} Term")

    info = Table([
        ["Student Name:", student.name, "Class:", cls],
        ["Roll No:", str(student.roll_no), "Father Name:", student.father_name or "—"],
        ["Issue Date:", timezone.localdate().strftime("%Y-%m-%d"), "Position:", f"{rank} of {strength}"],
    ], colWidths=[70, 170, 70, 150])
    info.setStyle(TableStyle([
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#d1d5db")),
        ("INNERGRID", (0,0), (-1,-1), 0.25, colors.HexColor("#e5e7eb")),
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#f9fafb")),
    ]))
    story.append(info)
    story.append(Spacer(1, 14))

    data = [["Subject", "Total", "Obtained", "%", "Grade", "Status"]] + rows
    data.append(["TOTAL", f"{total_marks:.0f}", f"{total_obtained:.2f}", f"{overall_pct:.1f}%", grade_of(overall_pct), "PASS" if overall_pct >= 50 else "FAIL"])

    t = Table(data, colWidths=[150, 60, 70, 60, 55, 60])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 9),
        ("ALIGN", (1,0), (-1,-1), "CENTER"),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#d1d5db")),
        ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f3f4f6")]),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#fde8dc")),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    story.append(Paragraph(f"<b>Teacher's Remarks:</b> {escape(teacher_remarks)}", small))
    story.append(Spacer(1, 22))

    sign = Table([
        ["_____________________", "_____________________", "_____________________"],
        ["Class Teacher", "Principal", "Parent / Guardian"],
    ], colWidths=[160, 160, 160])
    sign.setStyle(TableStyle([("ALIGN", (0,0), (-1,-1), "CENTER"), ("FONTSIZE", (0,0), (-1,-1), 9), ("TEXTCOLOR", (0,1), (-1,1), colors.grey)]))
    story.append(sign)

    doc.build(story)
    return response
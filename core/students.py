from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib import messages
from .models import CoreStudent as Student

def student_list(request):
    selected_class = request.GET.get('class', '').strip()
    status_filter = request.GET.get('status', '').strip()
    search_query = request.GET.get('q', '').strip()
    
    students = Student.objects.all().order_by('-id')

    if selected_class:
        students = students.filter(student_class__iexact=selected_class)

    if status_filter == 'active':
        students = students.filter(is_active=True)
    elif status_filter == 'inactive':
        students = students.filter(is_active=False)

    if search_query:
        students = students.filter(
            Q(name__icontains=search_query) | 
            Q(roll_no__icontains=search_query) |
            Q(father_name__icontains=search_query)
        )

    context = {
        "students": students,
        "selected_class": selected_class,
        "status_filter": status_filter,
        "search_query": search_query,
    }
    return render(request, "students.html", context)

def student_create(request):
    if request.method == "POST":
        student = Student(
            name=request.POST.get('name'),
            father_name=request.POST.get('father_name'),
            father_cnic=request.POST.get('father_cnic') or None,
            student_class=request.POST.get('student_class'),
            roll_no=request.POST.get('roll_no'),
            dob=request.POST.get('dob') or None,
            enrolment_date=request.POST.get('enrolment_date') or None,
            gender=request.POST.get('gender') or None,
            contact=request.POST.get('contact') or None,
            address=request.POST.get('address') or None,
            previous_school=request.POST.get('previous_school') or None,
            is_active=request.POST.get('is_active') == '1',
            admission_fee=request.POST.get('admission_fee') or 0.00,
            monthly_fee=request.POST.get('monthly_fee') or 0.00,
            transport_charges=request.POST.get('transport_charges') or 0.00,
            other_charges=request.POST.get('other_charges') or 0.00,
        )
        if 'photo' in request.FILES:
            student.photo = request.FILES['photo']
        if 'form_b_image' in request.FILES:
            student.form_b_image = request.FILES['form_b_image']
            
        student.save()
        messages.success(request, f'Student "{student.name}" registered successfully!')
    return redirect("student_list")

def student_update(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == "POST":
        student.name = request.POST.get('name')
        student.father_name = request.POST.get('father_name')
        student.father_cnic = request.POST.get('father_cnic') or None
        student.student_class = request.POST.get('student_class')
        student.roll_no = request.POST.get('roll_no')
        student.dob = request.POST.get('dob') or None
        student.enrolment_date = request.POST.get('enrolment_date') or None
        student.gender = request.POST.get('gender') or None
        student.contact = request.POST.get('contact') or None
        student.address = request.POST.get('address') or None
        student.previous_school = request.POST.get('previous_school') or None
        student.is_active = request.POST.get('is_active') == '1'
        student.admission_fee = request.POST.get('admission_fee') or 0.00
        student.monthly_fee = request.POST.get('monthly_fee') or 0.00
        student.transport_charges = request.POST.get('transport_charges') or 0.00
        student.other_charges = request.POST.get('other_charges') or 0.00

        if 'photo' in request.FILES:
            student.photo = request.FILES['photo']
        if 'form_b_image' in request.FILES:
            student.form_b_image = request.FILES['form_b_image']

        student.save()
        messages.success(request, f'Student "{student.name}" updated successfully!')
    return redirect("student_list")

def student_toggle_status(request, pk):
    student = get_object_or_404(Student, pk=pk)
    student.is_active = not student.is_active
    student.save()
    status_str = "Active" if student.is_active else "Deactivated"
    messages.success(request, f'Student "{student.name}" is now {status_str}.')
    return redirect("student_list")

def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == "POST":
        name = student.name
        student.delete()
        messages.success(request, f'Student "{name}" removed successfully!')
    return redirect("student_list")
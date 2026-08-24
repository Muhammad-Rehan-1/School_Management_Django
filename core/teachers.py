from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib import messages
from .models import CoreTeacher as Teacher

def teacher_list(request):
    search_query = request.GET.get('q', '').strip()
    teachers = Teacher.objects.all().order_by('-id')

    if search_query:
        teachers = teachers.filter(
            Q(name__icontains=search_query) | 
            Q(emp_id__icontains=search_query) |
            Q(subject__icontains=search_query) |
            Q(cnic__icontains=search_query)
        )

    context = {
        "teachers": teachers,
        "search_query": search_query,
    }
    return render(request, "teachers.html", context)

def teacher_create(request):
    if request.method == "POST":
        teacher = Teacher(
            name=request.POST.get('name'),
            emp_id=request.POST.get('emp_id'),
            cnic=request.POST.get('cnic') or None,
            subject=request.POST.get('subject'),
            qualification=request.POST.get('qualification') or None,
            salary=request.POST.get('salary') or 0.00,
            joining_date=request.POST.get('joining_date') or None,
            gender=request.POST.get('gender') or None,
            contact=request.POST.get('contact') or None,
            emergency_contact=request.POST.get('emergency_contact') or None,
            email=request.POST.get('email') or None,
        )
        if 'photo' in request.FILES:
            teacher.photo = request.FILES['photo']
        if 'cnic_photo' in request.FILES:
            teacher.cnic_photo = request.FILES['cnic_photo']
            
        teacher.save()
        messages.success(request, f'Teacher "{teacher.name}" registered successfully!')
    return redirect("teacher_list")

def teacher_update(request, pk):
    teacher = get_object_or_404(Teacher, pk=pk)
    if request.method == "POST":
        teacher.name = request.POST.get('name')
        teacher.emp_id = request.POST.get('emp_id')
        teacher.cnic = request.POST.get('cnic') or None
        teacher.subject = request.POST.get('subject')
        teacher.qualification = request.POST.get('qualification') or None
        teacher.salary = request.POST.get('salary') or 0.00
        teacher.joining_date = request.POST.get('joining_date') or None
        teacher.gender = request.POST.get('gender') or None
        teacher.contact = request.POST.get('contact') or None
        teacher.emergency_contact = request.POST.get('emergency_contact') or None
        teacher.email = request.POST.get('email') or None

        if 'photo' in request.FILES:
            teacher.photo = request.FILES['photo']
        if 'cnic_photo' in request.FILES:
            teacher.cnic_photo = request.FILES['cnic_photo']

        teacher.save()
        messages.success(request, f'Teacher "{teacher.name}" updated successfully!')
    return redirect("teacher_list")

def teacher_delete(request, pk):
    teacher = get_object_or_404(Teacher, pk=pk)
    if request.method == "POST":
        name = teacher.name
        teacher.delete()
        messages.success(request, f'Teacher "{name}" removed successfully!')
    return redirect("teacher_list")
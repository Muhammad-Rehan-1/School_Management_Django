from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib import messages
from .models import CoreStaff as Staff

def staff_list(request):
    search_query = request.GET.get('q', '').strip()
    staff_members = Staff.objects.all().order_by('-id')

    if search_query:
        staff_members = staff_members.filter(
            Q(name__icontains=search_query) | 
            Q(emp_id__icontains=search_query) |
            Q(role__icontains=search_query) |
            Q(cnic__icontains=search_query)
        )

    context = {
        "staff_members": staff_members,
        "search_query": search_query,
    }
    return render(request, "staff.html", context)

def staff_create(request):
    if request.method == "POST":
        staff = Staff(
            name=request.POST.get('name'),
            emp_id=request.POST.get('emp_id'),
            cnic=request.POST.get('cnic') or None,
            role=request.POST.get('role'),
            qualification=request.POST.get('qualification') or None,
            salary=request.POST.get('salary') or 0.00,
            joining_date=request.POST.get('joining_date') or None,
            gender=request.POST.get('gender') or None,
            contact=request.POST.get('contact') or None,
            emergency_contact=request.POST.get('emergency_contact') or None,
            email=request.POST.get('email') or None,
        )
        if 'photo' in request.FILES:
            staff.photo = request.FILES['photo']
        if 'cnic_photo' in request.FILES:
            staff.cnic_photo = request.FILES['cnic_photo']

        staff.save()
        messages.success(request, f'Employee "{staff.name}" added successfully!')
    return redirect("staff_list")

def staff_update(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    if request.method == "POST":
        staff.name = request.POST.get('name')
        staff.emp_id = request.POST.get('emp_id')
        staff.cnic = request.POST.get('cnic') or None
        staff.role = request.POST.get('role')
        staff.qualification = request.POST.get('qualification') or None
        staff.salary = request.POST.get('salary') or 0.00
        staff.joining_date = request.POST.get('joining_date') or None
        staff.gender = request.POST.get('gender') or None
        staff.contact = request.POST.get('contact') or None
        staff.emergency_contact = request.POST.get('emergency_contact') or None
        staff.email = request.POST.get('email') or None

        if 'photo' in request.FILES:
            staff.photo = request.FILES['photo']
        if 'cnic_photo' in request.FILES:
            staff.cnic_photo = request.FILES['cnic_photo']

        staff.save()
        messages.success(request, f'Employee "{staff.name}" updated successfully!')
    return redirect("staff_list")

def staff_delete(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    if request.method == "POST":
        name = staff.name
        staff.delete()
        messages.success(request, f'Employee "{name}" deleted successfully!')
    return redirect("staff_list")
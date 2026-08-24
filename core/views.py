from django.shortcuts import render, redirect, get_object_or_404

def dashboard(request):
    """
    Renders the main dashboard template.
    You can query MS SQL models here later to pass dynamic counts/records.
    """
    context = {
        # Placeholders for future database queries:
        # "total_students": Student.objects.count(),
        # "total_employees": Employee.objects.count(),
    }
    return render(request, "dashboard.html", context)



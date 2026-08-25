from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection

def class_section_list(request):
    classes = []
    total_capacity = 0
    
    with connection.cursor() as cursor:
        cursor.execute("SELECT [class], section, room_number, max_capacity, status FROM Class_defination ORDER BY [class], section")
        columns = [col[0] for col in cursor.description]
        classes = [dict(zip(columns, row)) for row in cursor.fetchall()]
        unique_classes = set(c['class'] for c in classes)
        total_capacity = sum(int(c['max_capacity']) for c in classes if c['max_capacity'] and str(c['max_capacity']).isdigit())

    if request.method == 'POST':
        class_name = request.POST.get('class_field')
        section_name = request.POST.get('section')
        room_number = request.POST.get('room_number')
        max_capacity = request.POST.get('max_capacity')
        status = request.POST.get('status', 'Active')

        if class_name and section_name and max_capacity:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM Class_defination WHERE [class] = %s AND section = %s", [class_name, section_name])
                exists = cursor.fetchone()[0]

                if exists == 0:
                    cursor.execute("""
                        INSERT INTO Class_defination ([class], section, room_number, max_capacity, status, created_at) 
                        VALUES (%s, %s, %s, %s, %s, GETDATE())
                    """, [class_name, section_name, room_number, max_capacity, status])
                    messages.success(request, f"Class {class_name} - Section {section_name} added successfully!")
                else:
                    messages.error(request, "This Class and Section combination already exists.")
        else:
            messages.error(request, "Please fill all required fields.")

        return redirect('class_section_list')

    context = {
        'classes': classes,
        'total_classes': len(unique_classes),
        'total_sections': len(classes),
        'total_capacity': total_capacity,
    }
    return render(request, 'class_defination.html', context)


def delete_class_section(request):
    # Delete using Class and Section name since there is no ID
    if request.method == 'POST':
        class_name = request.POST.get('class_field')
        section_name = request.POST.get('section')
        
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM Class_defination WHERE [class] = %s AND section = %s", [class_name, section_name])
            messages.success(request, "Class/Section deleted successfully.")
            
    return redirect('class_section_list')

def update_class_section(request):
    if request.method == 'POST':
        old_class = request.POST.get('old_class')
        old_section = request.POST.get('old_section')
        new_class = request.POST.get('class_field')
        new_section = request.POST.get('section')
        room_number = request.POST.get('room_number')
        max_capacity = request.POST.get('max_capacity')
        status = request.POST.get('status', 'Active')

        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE Class_defination 
                SET [class] = %s, section = %s, room_number = %s, max_capacity = %s, status = %s 
                WHERE [class] = %s AND section = %s
            """, [new_class, new_section, room_number, max_capacity, status, old_class, old_section])
            
        messages.success(request, f"Class {new_class} - Section {new_section} updated successfully!")
        return redirect('class_section_list')
    
import json
from django.http import JsonResponse

def toggle_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            class_name = data.get('class_field')
            section_name = data.get('section')
            new_status = data.get('status')

            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE Class_defination 
                    SET status = %s 
                    WHERE [class] = %s AND section = %s
                """, [new_status, class_name, section_name])
            
            return JsonResponse({'success': True, 'message': f'Status updated to {new_status}'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
            
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)    
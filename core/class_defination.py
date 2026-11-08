from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection
from django.http import JsonResponse
import json


def _fetch_classes():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                [class] AS class_field,
                section,
                room_number,
                max_capacity,
                status
            FROM Class_defination
            ORDER BY [class], section
        """)
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    # pyodbc kabhi column name 'class' hi wapas karta hai — safety net
    for row in rows:
        if 'class_field' not in row and 'class' in row:
            row['class_field'] = row['class']
    return rows


def _get_room_owner(room_number, exclude_class=None, exclude_section=None):
    """
    Check karta hai ke diya gaya room number kisi aur class/section ko
    already allocate to nahi hai.
    Agar allocated hai to (class, section) tuple return karta hai, warna None.
    """
    room_number = (room_number or '').strip()
    if not room_number:
        return None

    sql = """
        SELECT TOP 1 [class], section
        FROM Class_defination
        WHERE LTRIM(RTRIM(room_number)) = %s
    """
    params = [room_number]

    if exclude_class is not None and exclude_section is not None:
        sql += " AND NOT ([class] = %s AND section = %s)"
        params.extend([exclude_class, exclude_section])

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()

    return (row[0], row[1]) if row else None


def _combination_exists(class_name, section_name, exclude_class=None, exclude_section=None):
    """
    Check karta hai ke Class + Section ka combination pehle se to nahi hai.
    Update ke waqt apna hi record exclude kar diya jata hai.
    """
    class_name = (class_name or '').strip()
    section_name = (section_name or '').strip()
    if not class_name or not section_name:
        return False

    sql = """
        SELECT COUNT(*)
        FROM Class_defination
        WHERE LTRIM(RTRIM([class])) = %s AND LTRIM(RTRIM(section)) = %s
    """
    params = [class_name, section_name]

    if exclude_class is not None and exclude_section is not None:
        sql += " AND NOT ([class] = %s AND section = %s)"
        params.extend([exclude_class, exclude_section])

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()[0] > 0


def class_section_list(request):
    if request.method == 'POST':
        class_name = (request.POST.get('class_field') or '').strip()
        section_name = (request.POST.get('section') or '').strip()
        room_number = (request.POST.get('room_number') or '').strip()
        max_capacity = (request.POST.get('max_capacity') or '').strip()
        status = (request.POST.get('status') or 'Active').strip()

        if class_name and section_name and max_capacity:
            # ---- CLASS + SECTION DUPLICATE CHECK ----
            if _combination_exists(class_name, section_name):
                messages.error(request, "This Class and Section combination already exists.")
                return redirect('class_section_list')

            # ---- ROOM NUMBER DUPLICATE CHECK ----
            owner = _get_room_owner(room_number)
            if owner:
                messages.error(
                    request,
                    f"Room {room_number} is already allocated to Class {owner[0]} - Section {owner[1]}. "
                    f"Please choose a different room number."
                )
                return redirect('class_section_list')

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO Class_defination
                        ([class], section, room_number, max_capacity, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, GETDATE())
                    """,
                    [class_name, section_name, room_number, max_capacity, status],
                )
            messages.success(
                request,
                f"Class {class_name} - Section {section_name} added successfully!",
            )
        else:
            messages.error(request, "Please fill all required fields.")

        return redirect('class_section_list')

    classes = _fetch_classes()
    unique_classes = set(c.get('class_field') for c in classes if c.get('class_field'))
    total_capacity = sum(
        int(c['max_capacity'])
        for c in classes
        if c.get('max_capacity') and str(c['max_capacity']).isdigit()
    )

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
        new_class = (request.POST.get('class_field') or '').strip()
        new_section = (request.POST.get('section') or '').strip()
        room_number = (request.POST.get('room_number') or '').strip()
        max_capacity = request.POST.get('max_capacity')
        status = request.POST.get('status', 'Active')

        if not new_class or not new_section or not max_capacity:
            messages.error(request, "Please fill all required fields.")
            return redirect('class_section_list')

        # ---- CLASS + SECTION DUPLICATE CHECK (apna record chhod kar) ----
        if _combination_exists(new_class, new_section,
                               exclude_class=old_class, exclude_section=old_section):
            messages.error(
                request,
                f"Class {new_class} - Section {new_section} already exists. "
                f"Please choose a different combination."
            )
            return redirect('class_section_list')

        # ---- ROOM NUMBER DUPLICATE CHECK (apna record chhod kar) ----
        owner = _get_room_owner(room_number, exclude_class=old_class, exclude_section=old_section)
        if owner:
            messages.error(
                request,
                f"Room {room_number} is already allocated to Class {owner[0]} - Section {owner[1]}. "
                f"Please choose a different room number."
            )
            return redirect('class_section_list')

        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE Class_defination 
                SET [class] = %s, section = %s, room_number = %s, max_capacity = %s, status = %s 
                WHERE [class] = %s AND section = %s
            """, [new_class, new_section, room_number, max_capacity, status, old_class, old_section])

        messages.success(request, f"Class {new_class} - Section {new_section} updated successfully!")
        return redirect('class_section_list')


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
from decimal import Decimal
from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import (
    CoreStaff as Staff,
    CoreStudent as Student,
    Vehicle,
    Route,
    Stop,
    StudentTransport,
)
from .user_rights import get_user_module_permissions

DRIVER_ROLES = ['Driver', 'Driver / Conductor', 'Conductor']


def _next_assignment_code():
    last = StudentTransport.objects.order_by('-id').first()
    n = 1

    if last and last.code and last.code.startswith('TA-'):
        try:
            n = int(last.code.split('-')[1]) + 1
        except (ValueError, IndexError):
            n = StudentTransport.objects.count() + 1

    code = f"TA-{n:04d}"
    while StudentTransport.objects.filter(code=code).exists():
        n += 1
        code = f"TA-{n:04d}"

    return code


@receiver(post_save, sender=Student)
def auto_unassign_on_student_deactivate(sender, instance, **kwargs):
    if not instance.is_active:
        qs = StudentTransport.objects.filter(student=instance, is_active=True)
        if qs.exists():
            today = date.today()
            for a in qs:
                a.is_active = False
                a.end_date = today
                a.save(update_fields=['is_active', 'end_date', 'updated_at'])

            Student.objects.filter(pk=instance.pk).update(transport_charges=Decimal('0.00'))


# ═══════════════════════════════════════════════════
# MAIN TRANSPORT PAGE (4 TABS)
# ═══════════════════════════════════════════════════

def transport_page(request):
    # ================= RIGHTS CHECK: VIEW =================
    perms = get_user_module_permissions(request.user, "transport")
    if not perms.get('can_view'):
        messages.error(request, "Access Denied: You do not have permission to view Transport Management.")
        return redirect('dashboard')

    tab = request.GET.get('tab', 'drivers')

    transport_staff = (
        Staff.objects
        .filter(role__in=DRIVER_ROLES, is_active=True)
        .select_related('vehicle')
        .order_by('emp_id')
    )

    vehicles = (
        Vehicle.objects
        .select_related('driver')
        .prefetch_related('routes', 'student_assignments')
        .all()
    )

    routes = (
        Route.objects
        .prefetch_related('stops', 'vehicles', 'vehicles__driver')
        .all()
    )

    aq       = request.GET.get('aq', '').strip()
    a_route  = request.GET.get('aroute', '').strip()
    a_veh    = request.GET.get('avehicle', '').strip()
    a_status = request.GET.get('astatus', '').strip()

    assignments = (
        StudentTransport.objects
        .select_related('student', 'route', 'vehicle', 'stop')
        .all()
    )

    if a_route:
        assignments = assignments.filter(route_id=a_route)
    if a_veh:
        assignments = assignments.filter(vehicle_id=a_veh)

    if a_status == 'active':
        assignments = assignments.filter(is_active=True)
    elif a_status == 'inactive':
        assignments = assignments.filter(is_active=False)

    if aq:
        assignments = assignments.filter(
            Q(code__icontains=aq) |
            Q(student__name__icontains=aq) |
            Q(student__roll_no__icontains=aq) |
            Q(vehicle__code__icontains=aq) |
            Q(route__name__icontains=aq)
        )

    total_capacity = sum(v.capacity for v in vehicles)
    total_riding   = StudentTransport.objects.filter(is_active=True).count()

    ctx = {
        'tab': tab,
        'drivers': transport_staff,
        'transport_staff': transport_staff,
        'vehicles': vehicles,
        'all_vehicles': Vehicle.objects.filter(status='Active'),
        'routes': routes,
        'all_routes': Route.objects.all(),
        'today': date.today().isoformat(),
        'default_end': (date.today() + timedelta(days=365)).isoformat(),
        'assignments': assignments,
        'aq': aq,
        'a_route': a_route,
        'a_vehicle': a_veh,
        'a_status': a_status,
        's_drivers': transport_staff.count(),
        's_vehicles': vehicles.count(),
        's_routes': routes.count(),
        's_riders': total_riding,
        's_free_seats': max(total_capacity - total_riding, 0),
        's_capacity': total_capacity,
        'next_assign_code': _next_assignment_code(),
        'next_route_code': f"R-{Route.objects.filter(code__startswith='R-').count() + 1:02d}",
        'next_bus_code': f"BUS-{Vehicle.objects.filter(vtype='Bus').count() + 1:03d}",
        'next_van_code': f"VAN-{Vehicle.objects.filter(vtype='Van').count() + 1:03d}",
        'next_cstr_code': f"CSTR-{Vehicle.objects.filter(vtype='Coaster').count() + 1:03d}",
        'perms': perms,
    }

    return render(request, 'transport.html', ctx)


def staff_detail_json(request, pk):
    perms = get_user_module_permissions(request.user, "transport")
    if not perms.get('can_view'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    d = get_object_or_404(Staff, pk=pk, is_active=True, role__in=DRIVER_ROLES)

    vehicle = None
    try:
        v = d.vehicle
        route = v.routes.first() if v else None
        vehicle = {
            'code': v.code,
            'name': v.name or v.vtype,
            'vtype': v.vtype,
            'reg_no': v.reg_no,
            'capacity': v.capacity,
            'used': v.used_seats,
            'route': route.code if route else '',
            'route_name': route.name if route else '',
        }
    except Exception:
        pass

    return JsonResponse({
        'id': d.pk,
        'code': d.emp_id,
        'name': d.name,
        'role': d.role,
        'cnic': d.cnic or '—',
        'contact': d.contact or '—',
        'email': d.email or '—',
        'qualification': d.qualification or '—',
        'salary': str(d.salary),
        'is_active': d.is_active,
        'photo': d.photo.url if d.photo else '',
        'cnic_photo': d.cnic_photo.url if d.cnic_photo else '',
        'vehicle': vehicle,
    })


# ═══════════════════════════════════════════════════
# VEHICLES
# ═══════════════════════════════════════════════════

def add_vehicle(request):
    perms = get_user_module_permissions(request.user, "transport")
    if not perms.get('can_add'):
        messages.error(request, "Access Denied: You do not have permission to add vehicles.")
        return redirect('/transport/?tab=vehicles')

    if request.method != 'POST':
        return redirect('transport_page')

    vtype = request.POST.get('vtype', 'Bus')
    prefix = {'Bus': 'BUS', 'Van': 'VAN', 'Coaster': 'CSTR'}.get(vtype, 'VEH')

    last = (
        Vehicle.objects
        .filter(vtype=vtype, code__startswith=f"{prefix}-")
        .order_by('-id').first()
    )

    n = Vehicle.objects.filter(code__startswith=f"{prefix}-").count() + 1
    if last and last.code.startswith(f"{prefix}-"):
        try:
            n = int(last.code.split('-')[1]) + 1
        except ValueError:
            pass

    code = f"{prefix}-{n:03d}"
    while Vehicle.objects.filter(code=code).exists():
        n += 1
        code = f"{prefix}-{n:03d}"

    driver_id = request.POST.get('driver') or None

    if driver_id:
        busy = Vehicle.objects.filter(driver_id=driver_id).first()
        if busy:
            d = Staff.objects.get(pk=driver_id)
            messages.error(
                request,
                f"{d.emp_id} ({d.name}) is already assigned to {busy.code}. One person = one vehicle."
            )
            return redirect('/transport/?tab=vehicles')

    Vehicle.objects.create(
        code=code,
        name=request.POST.get('name', '').strip() or code,
        vtype=vtype,
        reg_no=request.POST.get('reg_no', '').strip(),
        model_year=request.POST.get('model_year', '').strip(),
        capacity=int(request.POST.get('capacity') or 0),
        driver_id=driver_id,
        status=request.POST.get('status', 'Active'),
        notes=request.POST.get('notes', '').strip(),
    )

    messages.success(request, f"Vehicle saved as {code}")
    return redirect('/transport/?tab=vehicles')


def vehicle_detail(request, pk):
    perms = get_user_module_permissions(request.user, "transport")
    if not perms.get('can_view'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    v = get_object_or_404(
        Vehicle.objects.select_related('driver').prefetch_related('routes'),
        pk=pk,
    )

    riders = (
        v.student_assignments
        .filter(is_active=True)
        .select_related('student')[:50]
    )

    return JsonResponse({
        'code': v.code,
        'name': v.name,
        'vtype': v.vtype,
        'reg_no': v.reg_no,
        'model_year': v.model_year or '—',
        'capacity': v.capacity,
        'used': v.used_seats,
        'free': v.available_seats,
        'percent': v.occupancy_percent,
        'status': v.status,
        'notes': v.notes or '—',
        'driver': {
            'code': v.driver.emp_id,
            'name': v.driver.name,
            'phone': v.driver.contact or '',
        } if v.driver else None,
        'routes': [
            {'code': r.code, 'name': r.name, 'monthly_fee': str(r.monthly_fee)}
            for r in v.routes.all()
        ],
        'riders': [
            {
                'name': a.student.name,
                'roll_no': a.student.roll_no,
                'student_class': a.student.student_class,
            }
            for a in riders
        ],
    })


def edit_vehicle(request, pk):
    perms = get_user_module_permissions(request.user, "transport")
    if not perms.get('can_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit vehicles.")
        return redirect('/transport/?tab=vehicles')

    v = get_object_or_404(Vehicle, pk=pk)

    if request.method == 'POST':
        driver_id = request.POST.get('driver') or None

        if driver_id and str(driver_id) != str(v.driver_id):
            busy = (
                Vehicle.objects.filter(driver_id=driver_id)
                .exclude(pk=v.pk).first()
            )
            if busy:
                d = Staff.objects.get(pk=driver_id)
                messages.error(
                    request,
                    f"{d.emp_id} ({d.name}) is already assigned to {busy.code}."
                )
                return redirect('/transport/?tab=vehicles')

        new_cap = int(request.POST.get('capacity') or 0)

        if new_cap < v.used_seats:
            messages.error(
                request,
                f"Cannot set capacity to {new_cap} — {v.used_seats} students are already riding {v.code}."
            )
            return redirect('/transport/?tab=vehicles')

        v.name       = request.POST.get('name', '').strip() or v.code
        v.vtype      = request.POST.get('vtype', v.vtype)
        v.reg_no     = request.POST.get('reg_no', '').strip()
        v.model_year = request.POST.get('model_year', '').strip()
        v.capacity   = new_cap
        v.driver_id  = driver_id
        v.status     = request.POST.get('status', v.status)
        v.notes      = request.POST.get('notes', '').strip()
        v.save()

        messages.success(request, f"{v.code} updated")

    return redirect('/transport/?tab=vehicles')


@require_POST
def delete_vehicle(request, pk):
    perms = get_user_module_permissions(request.user, "transport")
    if not perms.get('can_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete vehicles.")
        return redirect('/transport/?tab=vehicles')

    v = get_object_or_404(Vehicle, pk=pk)

    if v.used_seats > 0:
        messages.error(
            request,
            f"Cannot delete {v.code} — {v.used_seats} students are assigned. Unassign them first."
        )
        return redirect('/transport/?tab=vehicles')

    code = v.code
    v.delete()
    messages.success(request, f"{code} deleted")
    return redirect('/transport/?tab=vehicles')


# ═══════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════

def add_route(request):
    perms = get_user_module_permissions(request.user, "transport")
    if not perms.get('can_add'):
        messages.error(request, "Access Denied: You do not have permission to add routes.")
        return redirect('/transport/?tab=routes')

    if request.method != 'POST':
        return redirect('transport_page')

    last = Route.objects.order_by('-id').first()
    n = Route.objects.filter(code__startswith='R-').count() + 1

    if last and last.code.startswith('R-'):
        try:
            n = int(last.code.split('-')[1]) + 1
        except ValueError:
            pass

    code = f"R-{n:02d}"
    while Route.objects.filter(code=code).exists():
        n += 1
        code = f"R-{n:02d}"

    route = Route.objects.create(
        code=code,
        name=request.POST.get('name', '').strip(),
        distance=request.POST.get('distance', '').strip(),
        monthly_fee=Decimal(request.POST.get('monthly_fee') or 0),
        pickup_start=request.POST.get('pickup_start') or None,
    )

    vehicle_ids = request.POST.getlist('vehicles')
    if vehicle_ids:
        route.vehicles.set(vehicle_ids)

    stop_names = request.POST.getlist('stop_name[]')
    stop_times = request.POST.getlist('stop_time[]')

    for i, name in enumerate(stop_names):
        name = name.strip()
        if not name:
            continue

        Stop.objects.create(
            route=route,
            name=name,
            time=stop_times[i] if i < len(stop_times) and stop_times[i] else None,
            order=i,
        )

    messages.success(request, f"Route saved as {code}")
    return redirect('/transport/?tab=routes')


def edit_route(request, pk):
    perms = get_user_module_permissions(request.user, "transport")
    if not perms.get('can_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit routes.")
        return redirect('/transport/?tab=routes')

    r = get_object_or_404(Route, pk=pk)

    if request.method == 'POST':
        r.name         = request.POST.get('name', '').strip()
        r.distance     = request.POST.get('distance', '').strip()
        r.monthly_fee  = Decimal(request.POST.get('monthly_fee') or 0)
        r.pickup_start = request.POST.get('pickup_start') or None
        r.save()

        r.vehicles.set(request.POST.getlist('vehicles'))
        r.stops.all().delete()

        stop_names = request.POST.getlist('stop_name[]')
        stop_times = request.POST.getlist('stop_time[]')

        for i, name in enumerate(stop_names):
            name = name.strip()
            if not name:
                continue

            Stop.objects.create(
                route=r,
                name=name,
                time=stop_times[i] if i < len(stop_times) and stop_times[i] else None,
                order=i,
            )

        messages.success(request, f"{r.code} updated")

    return redirect('/transport/?tab=routes')


@require_POST
def delete_route(request, pk):
    perms = get_user_module_permissions(request.user, "transport")
    if not perms.get('can_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete routes.")
        return redirect('/transport/?tab=routes')

    r = get_object_or_404(Route, pk=pk)
    riders = r.student_assignments.filter(is_active=True).count()

    if riders:
        messages.error(
            request,
            f"Cannot delete {r.code} — {riders} students are assigned to it."
        )
        return redirect('/transport/?tab=routes')

    code = r.code
    r.delete()
    messages.success(request, f"{code} deleted")
    return redirect('/transport/?tab=routes')


# ═══════════════════════════════════════════════════
# API HELPERS
# ═══════════════════════════════════════════════════

def api_student_suggest(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 1:
        return JsonResponse({'ok': True, 'results': []})

    students = (
        Student.objects.filter(is_active=True)
        .filter(
            Q(roll_no__icontains=q) |
            Q(name__icontains=q) |
            Q(father_name__icontains=q) 
        )
        .order_by('roll_no')[:10]
    )

    assigned_ids = set(
        StudentTransport.objects
        .filter(is_active=True, student__in=students)
        .values_list('student_id', flat=True)
    )

    return JsonResponse({
        'ok': True,
        'results': [
            {
                'id': s.pk,
                'name': s.name,
                'roll_no': s.roll_no,
                'student_class': s.student_class,
                'father_name': s.father_name or '',
                'photo': s.photo.url if s.photo else '',
                'assigned': s.pk in assigned_ids,
            }
            for s in students
        ],
    })


def api_student_by_roll(request):
    roll = request.GET.get('roll_no', '').strip()
    if not roll:
        return JsonResponse({'ok': False, 'error': 'Please enter a roll number.'}, status=400)

    student = Student.objects.filter(roll_no__iexact=roll).first()
    if not student:
        return JsonResponse({'ok': False, 'error': f'No student found with roll no "{roll}".'}, status=404)

    existing = (
        StudentTransport.objects
        .select_related('route', 'vehicle')
        .filter(student=student, is_active=True)
        .first()
    )

    return JsonResponse({
        'ok': True,
        'student': {
            'id': student.pk,
            'name': student.name,
            'roll_no': student.roll_no,
            'student_class': student.student_class,
            'father_name': student.father_name,
            'contact': student.contact or '',
            'address': student.address or '',
            'gender': student.gender or '',
            'is_active': student.is_active,
            'photo': student.photo.url if student.photo else '',
            'transport_charges': str(student.transport_charges or '0.00'),
        },
        'existing': {
            'code': existing.code,
            'route': f"{existing.route.code} — {existing.route.name}",
            'vehicle': f"{existing.vehicle.code} ({existing.vehicle.reg_no})",
        } if existing else None,
    })


def api_route_vehicles(request, pk):
    route = get_object_or_404(
        Route.objects.prefetch_related('vehicles__driver', 'stops'), pk=pk
    )

    vehicles = []
    for v in route.vehicles.all():
        used = v.used_seats
        free = max(v.capacity - used, 0)
        vehicles.append({
            'id': v.pk,
            'code': v.code,
            'name': v.name or v.vtype,
            'vtype': v.vtype,
            'reg_no': v.reg_no,
            'capacity': v.capacity,
            'used': used,
            'free': free,
            'percent': round((used / v.capacity) * 100) if v.capacity else 0,
            'status': v.status,
            'driver': v.driver.name if v.driver else '',
            'driver_phone': (v.driver.contact or '') if v.driver else '',
            'selectable': (free > 0 and v.status == 'Active'),
        })

    return JsonResponse({
        'ok': True,
        'route': {
            'id': route.pk,
            'code': route.code,
            'name': route.name,
            'distance': route.distance or '—',
            'monthly_fee': str(route.monthly_fee),
            'pickup_start': (
                route.pickup_start.strftime('%H:%M')
                if route.pickup_start else ''
            ),
        },
        'vehicles': vehicles,
        'stops': [
            {
                'id': s.pk,
                'name': s.name,
                'time': s.time.strftime('%H:%M') if s.time else '',
            }
            for s in route.stops.all()
        ],
    })


# ═══════════════════════════════════════════════════
# ASSIGN STUDENT → VEHICLE
# ═══════════════════════════════════════════════════

@require_POST
def assign_student_transport(request):
    perms = get_user_module_permissions(request.user, "transport")
    if not perms.get('can_add'):
        messages.error(request, "Access Denied: You do not have permission to assign transport.")
        return redirect('/transport/?tab=assign')

    student_id = request.POST.get('student_id')
    route_id   = request.POST.get('route')
    vehicle_id = request.POST.get('vehicle')

    if not (student_id and route_id and vehicle_id):
        messages.error(request, 'Student, route and vehicle are all required.')
        return redirect('/transport/?tab=assign')

    student = get_object_or_404(Student, pk=student_id, is_active=True)
    route   = get_object_or_404(Route, pk=route_id)
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)

    if StudentTransport.objects.filter(student=student, is_active=True).exists():
        messages.error(request, f'{student.name} ({student.roll_no}) is already assigned. Unassign first.')
        return redirect('/transport/?tab=assign')

    if not route.vehicles.filter(pk=vehicle.pk).exists():
        messages.error(request, f'{vehicle.code} does not run on {route.code}.')
        return redirect('/transport/?tab=assign')

    if vehicle.used_seats >= vehicle.capacity:
        messages.error(request, f'{vehicle.code} is full ({vehicle.capacity}/{vehicle.capacity}).')
        return redirect('/transport/?tab=assign')

    if vehicle.status != 'Active':
        messages.error(request, f'{vehicle.code} is "{vehicle.status}" and cannot take students.')
        return redirect('/transport/?tab=assign')

    fee = student.transport_charges or Decimal('0.00')

    start_raw = request.POST.get('start_date') or ''
    end_raw   = request.POST.get('end_date') or ''

    try:
        start_date = date.fromisoformat(start_raw) if start_raw else date.today()
        end_date   = date.fromisoformat(end_raw) if end_raw else None
    except ValueError:
        messages.error(request, 'Invalid start or end date.')
        return redirect('/transport/?tab=assign')

    if end_date and end_date < start_date:
        messages.error(request, 'End date cannot be before the start date.')
        return redirect('/transport/?tab=assign')

    a = StudentTransport.objects.create(
        code=_next_assignment_code(),
        student=student,
        route=route,
        vehicle=vehicle,
        stop_id=request.POST.get('stop') or None,
        monthly_fee=fee,
        pickup_point=request.POST.get('pickup_point', '').strip(),
        guardian_contact=request.POST.get('guardian_contact', '').strip(),
        start_date=start_date,
        end_date=end_date,
        notes=request.POST.get('notes', '').strip(),
        is_active=True,
    )

    messages.success(
        request,
        f'✓ {student.name} assigned to {vehicle.code} on {route.code} ({a.code}) with fee {fee}.'
    )
    return redirect('/transport/?tab=assign')


@require_POST
def edit_student_transport(request, pk):
    perms = get_user_module_permissions(request.user, "transport")
    if not perms.get('can_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit assignments.")
        return redirect('/transport/?tab=assign')

    a = get_object_or_404(StudentTransport, pk=pk)

    route   = get_object_or_404(Route, pk=request.POST.get('route'))
    vehicle = get_object_or_404(Vehicle, pk=request.POST.get('vehicle'))

    if not route.vehicles.filter(pk=vehicle.pk).exists():
        messages.error(request, f'{vehicle.code} does not run on {route.code}.')
        return redirect('/transport/?tab=assign')

    if vehicle.pk != a.vehicle_id and vehicle.used_seats >= vehicle.capacity:
        messages.error(request, f'{vehicle.code} is full.')
        return redirect('/transport/?tab=assign')

    start_raw = request.POST.get('start_date') or ''
    end_raw   = request.POST.get('end_date') or ''

    try:
        start_date = date.fromisoformat(start_raw) if start_raw else a.start_date
        end_date   = date.fromisoformat(end_raw) if end_raw else None
    except ValueError:
        messages.error(request, 'Invalid start or end date.')
        return redirect('/transport/?tab=assign')

    if end_date and start_date and end_date < start_date:
        messages.error(request, 'End date cannot be before the start date.')
        return redirect('/transport/?tab=assign')

    fee = a.student.transport_charges or Decimal('0.00')

    a.route            = route
    a.vehicle          = vehicle
    a.stop_id          = request.POST.get('stop') or None
    a.monthly_fee      = fee
    a.pickup_point     = request.POST.get('pickup_point', '').strip()
    a.guardian_contact = request.POST.get('guardian_contact', '').strip()
    a.start_date       = start_date
    a.end_date         = end_date
    a.notes            = request.POST.get('notes', '').strip()
    a.save()

    messages.success(request, f'{a.code} updated successfully.')
    return redirect('/transport/?tab=assign')


@require_POST
def reactivate_student_transport(request, pk):
    perms = get_user_module_permissions(request.user, "transport")
    if not perms.get('can_edit'):
        messages.error(request, "Access Denied: You cannot reactivate assignments.")
        return redirect('/transport/?tab=assign')

    a = get_object_or_404(StudentTransport, pk=pk)

    if not a.student.is_active:
        messages.error(
            request,
            f'{a.student.name} is currently deactivated. Activate the student from the Students module first.'
        )
        return redirect('/transport/?tab=assign')

    if StudentTransport.objects.filter(
        student=a.student, is_active=True
    ).exclude(pk=a.pk).exists():
        messages.error(request, f'{a.student.name} already has another active assignment.')
        return redirect('/transport/?tab=assign')

    if a.vehicle.used_seats >= a.vehicle.capacity:
        messages.error(request, f'{a.vehicle.code} is full.')
        return redirect('/transport/?tab=assign')

    a.is_active = True
    a.end_date  = None
    a.monthly_fee = a.student.transport_charges or Decimal('0.00')
    a.save(update_fields=['is_active', 'end_date', 'monthly_fee'])

    messages.success(request, f'{a.code} re-activated with fee {a.monthly_fee}.')
    return redirect('/transport/?tab=assign')


@require_POST
def unassign_student_transport(request, pk):
    perms = get_user_module_permissions(request.user, "transport")
    if not perms.get('can_delete') and not perms.get('can_edit'):
        messages.error(request, "Access Denied: You do not have permission to unassign students.")
        return redirect('/transport/?tab=assign')

    a = get_object_or_404(StudentTransport, pk=pk)
    a.is_active = False
    a.end_date  = date.today()
    a.save(update_fields=['is_active', 'end_date', 'updated_at'])

    a.student.transport_charges = 0
    a.student.save(update_fields=['transport_charges'])

    messages.success(
        request,
        f'{a.student.name} removed from {a.vehicle.code}. Seat freed — now {a.vehicle.used_seats}/{a.vehicle.capacity}.'
    )
    return redirect('/transport/?tab=assign')


@require_POST
def delete_student_transport(request, pk):
    perms = get_user_module_permissions(request.user, "transport")
    if not perms.get('can_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete assignments.")
        return redirect('/transport/?tab=assign')

    a = get_object_or_404(StudentTransport, pk=pk)
    code = a.code

    if a.is_active:
        a.student.transport_charges = 0
        a.student.save(update_fields=['transport_charges'])

    a.delete()
    messages.success(request, f'{code} deleted permanently.')
    return redirect('/transport/?tab=assign')


def assignment_detail_json(request, pk):
    perms = get_user_module_permissions(request.user, "transport")
    if not perms.get('can_view'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    a = get_object_or_404(
        StudentTransport.objects.select_related(
            'student', 'route', 'vehicle', 'vehicle__driver', 'stop'
        ),
        pk=pk,
    )

    return JsonResponse({
        'id': a.pk,
        'code': a.code,
        'student': {
            'id': a.student.pk,
            'name': a.student.name,
            'roll_no': a.student.roll_no,
            'student_class': a.student.student_class,
            'father_name': a.student.father_name,
            'contact': a.student.contact or '',
            'photo': a.student.photo.url if a.student.photo else '',
            'is_active': a.student.is_active,
        },
        'route': {
            'id': a.route.pk,
            'code': a.route.code,
            'name': a.route.name,
            'distance': a.route.distance or '—',
        },
        'vehicle': {
            'id': a.vehicle.pk,
            'code': a.vehicle.code,
            'reg_no': a.vehicle.reg_no,
            'vtype': a.vehicle.vtype,
            'capacity': a.vehicle.capacity,
            'used': a.vehicle.used_seats,
            'driver': a.vehicle.driver.name if a.vehicle.driver else '',
        },
        'stop': {'id': a.stop.pk, 'name': a.stop.name} if a.stop else None,
        'monthly_fee': str(a.monthly_fee),
        'pickup_point': a.pickup_point or '',
        'guardian_contact': a.guardian_contact or '',
        'start_date': a.start_date.isoformat() if a.start_date else '',
        'end_date': a.end_date.isoformat() if a.end_date else '',
        'is_active': a.is_active,
        'notes': a.notes or '',
    })
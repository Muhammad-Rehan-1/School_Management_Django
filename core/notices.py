from datetime import date, datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Notice, NCategory
from .user_rights import get_user_module_permissions


# =========================================================
# HELPER
# =========================================================

def _parse_date(value):
    """Convert form string YYYY-MM-DD to a date object, or None."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), '%Y-%m-%d').date()
    except (ValueError, TypeError, AttributeError):
        return None


# =========================================================
# NOTICE BOARD PAGE
# =========================================================

def notice_board(request):
    # ================= RIGHTS CHECK: VIEW =================
    perms = get_user_module_permissions(request.user, "notice")
    if not perms.get('can_view'):
        messages.error(request, "Access Denied: You do not have permission to view the Notice Board.")
        fallback = 'teacher_dashboard' if request.session.get('user_role') == 'Teacher' else 'dashboard'
        return redirect(request.META.get('HTTP_REFERER') or fallback)

    today = date.today()

    # Auto-expire published notices whose expiry date has passed
    Notice.objects.filter(
        status='Published',
        expiry_date__lt=today
    ).update(status='Expired')

    # Auto-publish scheduled notices whose publish date has arrived
    Notice.objects.filter(
        status='Scheduled',
        publish_date__lte=today,
        expiry_date__isnull=True
    ).update(status='Published')

    Notice.objects.filter(
        status='Scheduled',
        publish_date__lte=today,
        expiry_date__gte=today
    ).update(status='Published')

    # Prefetch category relationship
    notices = Notice.objects.select_related('author', 'category').all()
    categories = NCategory.objects.all().order_by('category_name')

    return render(request, 'notice_board.html', {
        'notices': notices,
        'categories': categories,
        'today': today,
        'perms': perms,
    })


# =========================================================
# AJAX: ADD CATEGORY
# =========================================================

@require_POST
def add_category_ajax(request):
    perms = get_user_module_permissions(request.user, "notice")
    if not perms.get('can_add') and not perms.get('can_edit'):
        return JsonResponse({'success': False, 'error': 'Permission Denied: You cannot add categories.'}, status=403)

    category_name = request.POST.get('category_name', '').strip()
    
    if not category_name:
        return JsonResponse({'success': False, 'error': 'Category name cannot be empty.'}, status=400)

    category, created = NCategory.objects.get_or_create(category_name=category_name)
    
    return JsonResponse({
        'success': True,
        'id': category.id,
        'category_name': category.category_name,
        'created': created
    })


# =========================================================
# ADD NOTICE
# =========================================================

def add_notice(request):
    # ================= RIGHTS CHECK: ADD =================
    perms = get_user_module_permissions(request.user, "notice")
    if not perms.get('can_add'):
        messages.error(request, "Access Denied: You do not have permission to publish notices.")
        return redirect('notice_board')

    if request.method != 'POST':
        return redirect('notice_board')

    last = Notice.objects.order_by('-id').first()
    n = 1

    if last and last.code and last.code.startswith('NTC-'):
        try:
            n = int(last.code.split('-')[1]) + 1
        except (ValueError, IndexError):
            n = Notice.objects.filter(code__startswith='NTC-').count() + 1

    code = f"NTC-{n:03d}"
    while Notice.objects.filter(code=code).exists():
        n += 1
        code = f"NTC-{n:03d}"

    title = request.POST.get('title', '').strip()
    body = request.POST.get('body', '').strip()
    
    cat_input = request.POST.get('category')
    category = None
    if cat_input:
        if cat_input.isdigit():
            category = NCategory.objects.filter(id=cat_input).first()
        else:
            category = NCategory.objects.filter(category_name=cat_input).first()

    priority = request.POST.get('priority', 'Normal')
    status = request.POST.get('status', 'Draft')
    audience = request.POST.getlist('audience[]') or request.POST.getlist('audience')
    pinned = request.POST.get('pinned') == 'on'

    publish_date = _parse_date(request.POST.get('publish_date'))
    expiry_date = _parse_date(request.POST.get('expiry_date'))

    if not title:
        messages.error(request, 'Notice title is required.')
        return redirect('notice_board')

    if not body:
        messages.error(request, 'Notice body is required.')
        return redirect('notice_board')

    if not audience:
        messages.error(request, 'Please select at least one audience.')
        return redirect('notice_board')

    if publish_date and expiry_date and expiry_date < publish_date:
        messages.error(request, 'Expiry date cannot be before the publish date.')
        return redirect('notice_board')

    if status == 'Published' and expiry_date and expiry_date < date.today():
        status = 'Expired'

    attachment = request.FILES.get('attachment')

    notice = Notice.objects.create(
        code=code,
        title=title,
        body=body,
        category=category,
        priority=priority,
        status=status,
        audience=list(audience),
        publish_date=publish_date,
        expiry_date=expiry_date,
        attachment=attachment,
        pinned=pinned,
        author=None,
    )

    messages.success(request, f"Notice saved as {notice.code}")
    return redirect('notice_board')


# =========================================================
# EDIT NOTICE
# =========================================================

def edit_notice(request, pk):
    # ================= RIGHTS CHECK: EDIT =================
    perms = get_user_module_permissions(request.user, "notice")
    if not perms.get('can_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit notices.")
        return redirect('notice_board')

    notice = get_object_or_404(Notice, pk=pk)

    if request.method != 'POST':
        return redirect('notice_board')

    title = request.POST.get('title', '').strip()
    body = request.POST.get('body', '').strip()
    
    cat_input = request.POST.get('category')
    if cat_input:
        if cat_input.isdigit():
            category = NCategory.objects.filter(id=cat_input).first()
        else:
            category = NCategory.objects.filter(category_name=cat_input).first()
    else:
        category = notice.category

    priority = request.POST.get('priority', notice.priority)
    status = request.POST.get('status', notice.status)
    audience = request.POST.getlist('audience[]') or request.POST.getlist('audience')
    pinned = request.POST.get('pinned') == 'on'

    publish_date = _parse_date(request.POST.get('publish_date'))
    expiry_date = _parse_date(request.POST.get('expiry_date'))

    if not title:
        messages.error(request, 'Notice title is required.')
        return redirect('notice_board')

    if not body:
        messages.error(request, 'Notice body is required.')
        return redirect('notice_board')

    if not audience:
        messages.error(request, 'Please select at least one audience.')
        return redirect('notice_board')

    if publish_date and expiry_date and expiry_date < publish_date:
        messages.error(request, 'Expiry date cannot be before the publish date.')
        return redirect('notice_board')

    if status == 'Published' and expiry_date and expiry_date < date.today():
        status = 'Expired'

    notice.title = title
    notice.body = body
    notice.category = category
    notice.priority = priority
    notice.status = status
    notice.audience = list(audience)
    notice.publish_date = publish_date
    notice.expiry_date = expiry_date
    notice.pinned = pinned

    new_file = request.FILES.get('attachment')
    if new_file:
        if notice.attachment:
            notice.attachment.delete(save=False)
        notice.attachment = new_file
    elif request.POST.get('remove_attachment') == '1':
        if notice.attachment:
            notice.attachment.delete(save=False)
        notice.attachment = None

    notice.save()

    messages.success(request, f"{notice.code} updated successfully")
    return redirect('notice_board')


# =========================================================
# PUBLISH DRAFT
# =========================================================

@require_POST
def publish_notice(request, pk):
    perms = get_user_module_permissions(request.user, "notice")
    if not perms.get('can_edit') and not perms.get('can_add'):
        messages.error(request, "Access Denied: You do not have permission to publish notices.")
        return redirect('notice_board')

    notice = get_object_or_404(Notice, pk=pk)

    if notice.status != 'Draft':
        messages.error(request, f"{notice.code} is not a draft.")
        return redirect('notice_board')

    today = date.today()
    if notice.expiry_date and notice.expiry_date < today:
        messages.error(
            request,
            f"{notice.code} has already passed its expiry date. Edit the expiry date before publishing."
        )
        return redirect('notice_board')

    notice.status = 'Published'
    if not notice.publish_date:
        notice.publish_date = today

    notice.save(update_fields=['status', 'publish_date', 'updated_at'])

    messages.success(request, f"{notice.code} published successfully.")
    return redirect('notice_board')


# =========================================================
# DELETE NOTICE
# =========================================================

@require_POST
def delete_notice(request, pk):
    perms = get_user_module_permissions(request.user, "notice")
    if not perms.get('can_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete notices.")
        return redirect('notice_board')

    notice = get_object_or_404(Notice, pk=pk)
    code = notice.code

    if notice.attachment:
        notice.attachment.delete(save=False)

    notice.delete()

    messages.success(request, f"{code} deleted")
    return redirect('notice_board')


# =========================================================
# PIN / UNPIN
# =========================================================

@require_POST
def toggle_pin_notice(request, pk):
    perms = get_user_module_permissions(request.user, "notice")
    if not perms.get('can_edit'):
        messages.error(request, "Access Denied: You do not have permission to pin notices.")
        return redirect('notice_board')

    notice = get_object_or_404(Notice, pk=pk)
    notice.pinned = not notice.pinned
    notice.save(update_fields=['pinned', 'updated_at'])

    messages.success(
        request,
        f"{notice.code} pinned to top." if notice.pinned else f"{notice.code} unpinned."
    )
    return redirect('notice_board')


# =========================================================
# DETAIL JSON
# =========================================================

def notice_detail_json(request, pk):
    perms = get_user_module_permissions(request.user, "notice")
    if not perms.get('can_view'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    notice = get_object_or_404(Notice.objects.select_related('category'), pk=pk)

    if request.GET.get('mode') != 'edit':
        notice.views += 1
        notice.save(update_fields=['views'])

    if notice.author:
        author_name = notice.author.get_full_name() or notice.author.username
    else:
        author_name = 'Admin'

    attachment = None
    if notice.attachment:
        attachment = {
            'name': notice.attachment.name.split('/')[-1],
            'url': notice.attachment.url,
        }

    return JsonResponse({
        'id': notice.pk,
        'code': notice.code,
        'title': notice.title,
        'body': notice.body,
        'category_id': notice.category.id if notice.category else None,
        'category': notice.category.category_name if notice.category else 'General',
        'priority': notice.priority,
        'status': notice.status,
        'audience': notice.audience or [],
        'publish_date': notice.publish_date.isoformat() if notice.publish_date else '',
        'expiry_date': notice.expiry_date.isoformat() if notice.expiry_date else '',
        'attachment': attachment,
        'pinned': notice.pinned,
        'views': notice.views,
        'author': author_name,
        'created_at': notice.created_at.strftime('%Y-%m-%d %H:%M'),
    })


def notice_print(request, pk):
    # ================= RIGHTS CHECK: PRINT =================
    perms = get_user_module_permissions(request.user, "notice")
    if not perms.get('can_print'):
        messages.error(request, "Access Denied: You do not have permission to print notices.")
        return redirect('notice_board')

    notice = get_object_or_404(Notice.objects.select_related('category'), pk=pk)

    if notice.status != 'Published':
        messages.error(request, 'Only published notices can be printed.')
        return redirect('notice_board')

    if notice.author:
        author_name = notice.author.get_full_name() or notice.author.username
    else:
        author_name = 'Admin'

    attachment_name = None
    if notice.attachment:
        attachment_name = notice.attachment.name.split('/')[-1]

    return render(request, 'notice_board_print.html', {
        'notice': notice,
        'author_name': author_name,
        'attachment_name': attachment_name,
    })
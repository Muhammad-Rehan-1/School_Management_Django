from datetime import date, datetime
from collections import OrderedDict
from calendar import monthrange
from django.shortcuts import render, redirect
from django.http import JsonResponse, Http404
from django.contrib import messages
from django.db.models import Sum, Count, Q

from .models import (
    CoreStudent, CoreStudentFee, CoreStaffPayroll,
    CoreExam, CoreExamMark, ClassDefination,
    Vehicle, Route,
)
from .user_rights import get_user_module_permissions

PASS_PCT = 33
MN = ['January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December']


# ═══════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════

def _d(v):
    try:
        return datetime.strptime(v, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def _money(v):
    return 'Rs ' + f'{int(v or 0):,}'


def _fmt(d):
    return d.strftime('%d %b %Y') if d else '—'


def _grade(p):
    p = float(p or 0)
    if p >= 80: return 'A+'
    if p >= 70: return 'A'
    if p >= 60: return 'B'
    if p >= 50: return 'C'
    if p >= 40: return 'D'
    return 'F'


def _gtag(g):
    return {'A+': 't-green', 'A': 't-green', 'B': 't-blue',
            'C': 't-amber', 'D': 't-purple', 'F': 't-red'}.get(g, 't-grey')


def tag(v, cls):
    return {'v': str(v), 'tag': cls}


def box(label, value, bg, fg):
    return {'label': label, 'value': str(value), 'bg': bg, 'fg': fg}


BLUE   = ('#E9F0FC', '#3F68B4')
GREEN  = ('#E5F6EE', '#2A9364')
AMBER  = ('#FEF2E4', '#C67C2E')
RED    = ('#FDECEC', '#C94A48')
PURPLE = ('#F0EDFB', '#6B5CC4')


class Period:
    def __init__(self, req):
        self.mode  = req.GET.get('mode', 'single')
        self.d1    = _d(req.GET.get('date1')) or date.today()
        self.d2    = _d(req.GET.get('date2')) or date.today()
        self.month = int(req.GET.get('month') or date.today().month)
        self.year  = int(req.GET.get('year') or date.today().year)

    def label(self):
        if self.mode == 'month':
            return f'{MN[self.month - 1]} {self.year}'
        if self.mode == 'range':
            return f'{_fmt(self.d1)}  to  {_fmt(self.d2)}'
        return _fmt(self.d1)

    def by_date(self, qs, field):
        if self.mode == 'month':
            return qs.filter(**{f'{field}__month': self.month,
                                f'{field}__year': self.year})
        if self.mode == 'range':
            return qs.filter(**{f'{field}__range': (self.d1, self.d2)})
        return qs.filter(**{field: self.d1})

    def by_fee_month(self, qs):
        if self.mode == 'month':
            return qs.filter(fee_month=self.month, fee_year=self.year)
        if self.mode == 'range':
            return qs.filter(due_date__range=(self.d1, self.d2))
        return qs.filter(fee_month=self.d1.month, fee_year=self.d1.year)

    def payroll_my(self):
        if self.mode == 'month':
            return self.month, self.year
        return self.d1.month, self.d1.year


# ═══════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════

META = OrderedDict([
    ('defaulters', dict(label='Fee Defaulters List',     group='💰 Fee Reports',       needs=['class'],         date='month')),
    ('collection', dict(label='Monthly Fee Collection',  group='💰 Fee Reports',       needs=[],                date='month')),
    ('challan',    dict(label='Challan Register',        group='💰 Fee Reports',       needs=['class'],         date='month')),
    ('daily',      dict(label='Daily Collection Sheet',  group='💰 Fee Reports',       needs=[],                date='single')),
    ('result',     dict(label='Class Result Sheet',      group='📝 Exam Reports',      needs=['class', 'term'], date='none')),
    ('subject',    dict(label='Subject Performance',     group='📝 Exam Reports',      needs=['class', 'term'], date='none')),
    ('salary',     dict(label='Monthly Salary Sheet',    group='💵 Payroll Reports',   needs=[],                date='month')),
    ('pending',    dict(label='Pending Salary Payments', group='💵 Payroll Reports',   needs=[],                date='month')),
    ('manifest',   dict(label='Route Manifest',          group='🚌 Transport Reports', needs=['route'],         date='none')),
    ('occupancy',  dict(label='Vehicle Occupancy',       group='🚌 Transport Reports', needs=[],                date='none')),
    ('strength',   dict(label='Class-wise Strength',     group='🎓 Student Reports',   needs=[],                date='none')),
    ('directory',  dict(label='Student Directory',       group='🎓 Student Reports',   needs=['class'],         date='none')),
])


def _build(request):
    key = request.GET.get('type', '').strip()
    if key not in META:
        return None, 'Unknown report type.'

    P     = Period(request)
    cls   = request.GET.get('cls', '').strip()
    term  = request.GET.get('term', '').strip()
    route = request.GET.get('route', '').strip()

    try:
        data = BUILDERS[key](P, cls, term, route)
    except Exception as e:
        return None, f'Build error: {e}'

    sub = []
    if cls and 'class' in META[key]['needs']:
        sub.append(f'Class {cls}')
    if term and 'term' in META[key]['needs']:
        sub.append(term)
    if route and 'route' in META[key]['needs']:
        r = Route.objects.filter(pk=route).first()
        if r:
            sub.append(f'{r.code} {r.name}')

    data.update({
        'ok': True,
        'key': key,
        'title': META[key]['label'],
        'subtitle': ' · '.join(sub),
        'period': P.label() if META[key]['date'] != 'none' else 'All Records',
        'count': len(data.get('rows', [])),
    })
    return data, None


# ═══════════════════════════════════════════════════
# VIEWS
# ═══════════════════════════════════════════════════

def reports_page(request):
    # ================= RIGHTS CHECK: VIEW =================
    perms = get_user_module_permissions(request.user, "reports")
    if not perms.get('can_view'):
        messages.error(request, "Access Denied: You do not have permission to view Reports.")
        return redirect('dashboard')

    today = date.today()

    groups = OrderedDict()
    for k, m in META.items():
        groups.setdefault(m['group'], []).append({'key': k, 'label': m['label']})

    classes = list(
        CoreStudent.objects.exclude(student_class='')
        .values_list('student_class', flat=True).distinct().order_by('student_class')
    )

    terms = list(
        CoreExam.objects.exclude(term='')
        .values_list('term', flat=True).distinct().order_by('term')
    ) or ['Term 1', 'Term 2', 'Final']

    return render(request, 'reports.html', {
        'groups': groups,
        'meta_json': {k: v['needs'] for k, v in META.items()},
        'datemode_json': {k: v['date'] for k, v in META.items()},
        'classes': classes,
        'terms': terms,
        'routes': Route.objects.order_by('code'),
        'report_count': len(META),
        'today': today.isoformat(),
        'cur_month': today.month,
        'cur_year': today.year,
        'years': list(range(today.year + 1, today.year - 5, -1)),
        'months': [{'n': i + 1, 'name': m} for i, m in enumerate(MN)],
        'perms': perms,
    })


def report_data(request):
    perms = get_user_module_permissions(request.user, "reports")
    if not perms.get('can_view'):
        return JsonResponse({'ok': False, 'error': 'Permission Denied'}, status=403)

    data, err = _build(request)
    if err:
        return JsonResponse({'ok': False, 'error': err}, status=400)
    return JsonResponse(data)


def report_print(request):
    # ================= RIGHTS CHECK: PRINT =================
    perms = get_user_module_permissions(request.user, "reports")
    if not perms.get('can_print'):
        messages.error(request, "Access Denied: You do not have permission to print or export reports.")
        return redirect('reports_page')

    data, err = _build(request)
    if err:
        raise Http404(err)

    rows = []
    for r in data['rows']:
        cells = []
        for i, c in enumerate(r):
            if isinstance(c, dict):
                cells.append({'v': c['v'], 'tag': c['tag'],
                              'num': i in data['num']})
            else:
                cells.append({'v': c, 'tag': '', 'num': i in data['num']})
        rows.append(cells)

    cols = [{'v': c, 'num': i in data['num']}
            for i, c in enumerate(data['cols'])]

    foot = None
    if data.get('foot'):
        foot = [{'v': c, 'num': i in data['num']}
                for i, c in enumerate(data['foot'])]

    return render(request, 'reports_print.html', {
        'title': data['title'],
        'subtitle': data['subtitle'],
        'period': data['period'],
        'summary': data.get('summary', []),
        'cols': cols,
        'rows': rows,
        'foot': foot,
        'count': data['count'],
        'landscape': len(data['cols']) > 8,
        'generated': datetime.now(),
        'auto': request.GET.get('auto') == '1',
        'key': data['key'],
    })


# ═══════════════════════════════════════════════════
# REPORT BUILDERS
# ═══════════════════════════════════════════════════

def r_defaulters(P, cls, term, route):
    qs = CoreStudentFee.objects.select_related('student').filter(balance__gt=0)
    qs = P.by_fee_month(qs)
    if cls:
        qs = qs.filter(student__student_class__iexact=cls)
    qs = qs.order_by('-balance')[:400]

    today = date.today()
    rows = []
    t_tot = t_paid = t_bal = 0

    for f in qs:
        s = f.student
        try:
            last_day = monthrange(f.fee_year, f.fee_month)[1]
            fee_due_date = date(f.fee_year, f.fee_month, last_day)
            od = (today - fee_due_date).days if fee_due_date < today else 0
        except Exception:
            od = 0

        t_tot  += f.total_amount or 0
        t_paid += f.paid_amount or 0
        t_bal  += f.balance or 0

        rows.append([
            s.name,
            s.roll_no or '—',
            s.student_class or '—',
            s.father_name or '—',
            s.contact or '—',
            _money(f.total_amount),
            _money(f.paid_amount) if f.paid_amount else '—',
            _money(f.balance),
            tag(
                f'{od} days',
                't-red' if od > 45 else 't-amber' if od > 15 else 't-grey'
            ),
        ])

    return {
        'cols': ['Student', 'Roll No', 'Class', 'Father Name', 'Contact',
                 'Total', 'Paid', 'Balance', 'Overdue'],
        'num': [5, 6, 7],
        'rows': rows,
        'foot': ['TOTAL', '', '', '', '', _money(t_tot), _money(t_paid),
                 _money(t_bal), f'{len(rows)} students'] if rows else None,
        'summary': [
            box('Defaulters', len(rows), *RED),
            box('Total Billed', _money(t_tot), *BLUE),
            box('Recovered', _money(t_paid), *GREEN),
            box('Outstanding', _money(t_bal), *AMBER),
        ],
    }


def r_collection(P, cls, term, route):
    qs = P.by_fee_month(CoreStudentFee.objects.all())

    agg = (qs.values('student__student_class')
             .annotate(n=Count('id'), exp=Sum('total_amount'), col=Sum('paid_amount'))
             .order_by('student__student_class'))

    rows, T = [], dict(n=0, exp=0, col=0)
    for a in agg:
        exp, col = a['exp'] or 0, a['col'] or 0
        pct = round(col / exp * 100) if exp else 0
        T['n'] += a['n']; T['exp'] += exp; T['col'] += col

        rows.append([
            a['student__student_class'] or '—', a['n'],
            _money(exp), _money(col), _money(exp - col),
            tag(f'{pct}%', 't-green' if pct >= 90 else 't-amber' if pct >= 75 else 't-red'),
        ])

    rate = round(T['col'] / T['exp'] * 100) if T['exp'] else 0

    return {
        'cols': ['Class', 'Students', 'Expected', 'Collected', 'Outstanding', 'Rate'],
        'num': [1, 2, 3, 4],
        'rows': rows,
        'foot': ['TOTAL', T['n'], _money(T['exp']), _money(T['col']),
                 _money(T['exp'] - T['col']), f'{rate}%'] if rows else None,
        'summary': [
            box('Students', T['n'], *BLUE),
            box('Expected', _money(T['exp']), *PURPLE),
            box('Collected', _money(T['col']), *GREEN),
            box('Collection Rate', f'{rate}%', *AMBER),
        ],
    }


def r_challan(P, cls, term, route):
    qs = P.by_fee_month(CoreStudentFee.objects.select_related('student'))
    if cls:
        qs = qs.filter(student__student_class__iexact=cls)
    qs = qs.order_by('challan_no')[:500]

    rows, T, unpaid = [], dict(t=0, tr=0, tot=0, paid=0), 0

    for f in qs:
        st = f.status or 'Unpaid'
        if st != 'Paid':
            unpaid += 1
        T['t']    += f.tuition_fee or 0
        T['tr']   += f.transport_fee or 0
        T['tot']  += f.total_amount or 0
        T['paid'] += f.paid_amount or 0

        rows.append([
            f.challan_no, f.student.name, f.student.roll_no,
            f.student.student_class,
            _money(f.tuition_fee), _money(f.transport_fee),
            _money(f.total_amount),
            _money(f.paid_amount) if f.paid_amount else '—',
            tag(st, 't-green' if st == 'Paid' else 't-amber' if st == 'Partial' else 't-red'),
        ])

    return {
        'cols': ['Challan No', 'Student', 'Roll No', 'Class', 'Tuition',
                 'Transport', 'Total', 'Paid', 'Status'],
        'num': [4, 5, 6, 7],
        'rows': rows,
        'foot': ['TOTAL', '', '', '', _money(T['t']), _money(T['tr']),
                 _money(T['tot']), _money(T['paid']), f'{len(rows)}'] if rows else None,
        'summary': [
            box('Challans', len(rows), *BLUE),
            box('Billed', _money(T['tot']), *PURPLE),
            box('Received', _money(T['paid']), *GREEN),
            box('Unpaid', unpaid, *RED),
        ],
    }


def r_daily(P, cls, term, route):
    qs = (CoreStudentFee.objects.select_related('student')
          .filter(paid_amount__gt=0, payment_date__isnull=False))
    qs = P.by_date(qs, 'payment_date').order_by('payment_date', 'challan_no')[:500]

    rows, total, cash, digital = [], 0, 0, 0

    for f in qs:
        amt = f.paid_amount or 0
        total += amt
        meth = f.payment_method or 'Cash'
        if meth == 'Cash':
            cash += amt
        elif meth != 'Cheque':
            digital += amt

        rows.append([
            _fmt(f.payment_date), f.challan_no, f.student.name,
            f.student.roll_no, f.student.student_class,
            _money(amt),
            tag(meth, 't-green' if meth == 'Cash'
                      else 't-purple' if meth == 'Cheque' else 't-blue'),
        ])

    return {
        'cols': ['Date', 'Challan No', 'Student', 'Roll No', 'Class', 'Amount', 'Method'],
        'num': [5],
        'rows': rows,
        'foot': ['TOTAL', '', '', '', '', _money(total),
                 f'{len(rows)} txns'] if rows else None,
        'summary': [
            box('Transactions', len(rows), *BLUE),
            box('Total Received', _money(total), *GREEN),
            box('Cash', _money(cash), *AMBER),
            box('Digital', _money(digital), *PURPLE),
        ],
    }


def r_result(P, cls, term, route):
    if not cls:
        return {'cols': ['Notice'], 'rows': [['Please select a class to run this report.']],
                'num': [], 'foot': None, 'summary': []}

    exams = CoreExam.objects.filter(student_class__iexact=cls)
    if term:
        exams = exams.filter(term__iexact=term)

    subjects = list(exams.values_list('subject', flat=True).distinct().order_by('subject'))
    if not subjects:
        return {'cols': ['Notice'], 'rows': [['No exams found for this class / term.']],
                'num': [], 'foot': None, 'summary': []}

    totals = {e.subject: (e.total_marks or 100) for e in exams}
    grand = sum(totals.get(s, 100) for s in subjects)

    marks = CoreExamMark.objects.filter(exam__in=exams).select_related('student', 'exam')

    pool = {}
    for m in marks:
        st = m.student
        d = pool.setdefault(st.pk, {'n': st.name, 'r': st.roll_no, 'm': {}})
        d['m'][m.exam.subject] = float(m.obtained_marks or 0)

    recs = []
    for d in pool.values():
        obt = sum(d['m'].get(s, 0) for s in subjects)
        pct = round(obt / grand * 100, 1) if grand else 0
        recs.append({**d, 'obt': obt, 'pct': pct})

    recs.sort(key=lambda x: -x['obt'])

    rows = []
    for i, r in enumerate(recs, 1):
        g = _grade(r['pct'])
        rows.append(
            [i, r['n'], r['r']] +
            [int(r['m'].get(s, 0)) for s in subjects] +
            [int(r['obt']), f"{r['pct']}%", tag(g, _gtag(g))]
        )

    pcts = [r['pct'] for r in recs] or [0]
    ncol = 3 + len(subjects)

    return {
        'cols': ['Pos', 'Student', 'Roll No'] + subjects + ['Total', '%', 'Grade'],
        'num': [0] + list(range(3, ncol + 2)),
        'rows': rows,
        'foot': None,
        'summary': [
            box('Students', len(recs), *BLUE),
            box('Class Average', f'{round(sum(pcts) / len(pcts), 1)}%', *GREEN),
            box('Highest', f'{max(pcts)}%', *PURPLE),
            box('Lowest', f'{min(pcts)}%', *RED),
        ],
    }


def r_subject(P, cls, term, route):
    exams = CoreExam.objects.all()
    if cls:
        exams = exams.filter(student_class__iexact=cls)
    if term:
        exams = exams.filter(term__iexact=term)

    rows, tp, tf = [], 0, 0

    for sub in exams.values_list('subject', flat=True).distinct().order_by('subject'):
        se = exams.filter(subject=sub)
        tot = (se.first().total_marks or 100)
        ms = [float(x or 0) for x in
              CoreExamMark.objects.filter(exam__in=se).values_list('obtained_marks', flat=True)]
        if not ms:
            continue

        cut = tot * PASS_PCT / 100
        p = sum(1 for x in ms if x >= cut)
        f = len(ms) - p
        tp += p; tf += f
        rate = round(p / len(ms) * 100)

        rows.append([
            sub, len(ms), round(sum(ms) / len(ms), 1),
            int(max(ms)), int(min(ms)), p, f,
            tag(f'{rate}%', 't-green' if rate >= 90 else 't-amber' if rate >= 75 else 't-red'),
        ])

    avg = round(sum(r[2] for r in rows) / len(rows), 1) if rows else 0

    return {
        'cols': ['Subject', 'Students', 'Average', 'Highest', 'Lowest', 'Pass', 'Fail', 'Pass Rate'],
        'num': [1, 2, 3, 4, 5, 6],
        'rows': rows,
        'foot': None,
        'summary': [
            box('Subjects', len(rows), *BLUE),
            box('Overall Avg', avg, *GREEN),
            box('Total Pass', tp, *PURPLE),
            box('Total Fail', tf, *RED),
        ],
    }


def _payroll(P, only_pending=False):
    m, y = P.payroll_my()
    qs = (CoreStaffPayroll.objects.select_related('teacher', 'staff')
          .filter(payroll_month=m, payroll_year=y))
    if only_pending:
        qs = qs.exclude(status='Paid')
    return qs.order_by('employee_type', 'id')


def r_salary(P, cls, term, route):
    rows, T = [], dict(b=0, a=0, d=0, n=0)

    for p in _payroll(P):
        emp = p.teacher or p.staff
        if not emp:
            continue
        net = (p.basic_salary or 0) + (p.extra_allowance or 0) - (p.deduction or 0)
        T['b'] += p.basic_salary or 0
        T['a'] += p.extra_allowance or 0
        T['d'] += p.deduction or 0
        T['n'] += net

        role = getattr(emp, 'subject', None) or getattr(emp, 'role', '—')

        rows.append([
            emp.emp_id, emp.name,
            tag(p.employee_type, 't-blue' if p.employee_type == 'Teacher' else 't-grey'),
            role,
            _money(p.basic_salary), _money(p.extra_allowance),
            _money(p.deduction) if p.deduction else '—',
            _money(net),
            tag(p.status, 't-green' if p.status == 'Paid' else 't-amber'),
        ])

    return {
        'cols': ['Emp ID', 'Name', 'Type', 'Designation', 'Basic',
                 'Allowance', 'Deduction', 'Net Salary', 'Status'],
        'num': [4, 5, 6, 7],
        'rows': rows,
        'foot': ['TOTAL', '', '', '', _money(T['b']), _money(T['a']),
                 _money(T['d']), _money(T['n']), f'{len(rows)}'] if rows else None,
        'summary': [
            box('Employees', len(rows), *BLUE),
            box('Gross', _money(T['b'] + T['a']), *PURPLE),
            box('Deductions', _money(T['d']), *RED),
            box('Net Payable', _money(T['n']), *GREEN),
        ],
    }


def r_pending(P, cls, term, route):
    rows, due = [], 0

    for p in _payroll(P, only_pending=True):
        emp = p.teacher or p.staff
        if not emp:
            continue
        net = (p.basic_salary or 0) + (p.extra_allowance or 0) - (p.deduction or 0)
        due += net
        role = getattr(emp, 'subject', None) or getattr(emp, 'role', '—')

        rows.append([
            emp.emp_id, emp.name,
            tag(p.employee_type, 't-blue' if p.employee_type == 'Teacher' else 't-grey'),
            role, _money(net),
            tag(p.status or 'Pending', 't-amber'),
        ])

    m, y = P.payroll_my()
    total = CoreStaffPayroll.objects.filter(payroll_month=m, payroll_year=y).count()

    return {
        'cols': ['Emp ID', 'Name', 'Type', 'Designation', 'Net Salary', 'Status'],
        'num': [4],
        'rows': rows,
        'foot': ['TOTAL', '', '', '', _money(due), f'{len(rows)}'] if rows else None,
        'summary': [
            box('Pending', len(rows), *AMBER),
            box('Amount Due', _money(due), *RED),
            box('Already Paid', total - len(rows), *GREEN),
            box('Total Staff', total, *BLUE),
        ],
    }


def r_manifest(P, cls, term, route):
    qs = Route.objects.prefetch_related('vehicles__driver', 'stops').order_by('code')
    if route:
        qs = qs.filter(pk=route)

    rows, cap, used = [], 0, 0

    for r in qs:
        stops = ' | '.join(
            f"{s.name} {s.time.strftime('%H:%M') if s.time else ''}".strip()
            for s in r.stops.all()
        ) or '—'

        vs = list(r.vehicles.all())
        if not vs:
            rows.append([r.code, r.name, '—', '—', '—', '—', 0, 0, stops])
            continue

        for v in vs:
            u = v.used_seats
            cap += v.capacity
            used += u
            drv = v.driver
            rows.append([
                r.code, r.name, v.code, v.reg_no,
                drv.name if drv else '—',
                (drv.contact if drv else '') or '—',
                v.capacity, u, stops,
            ])

    return {
        'cols': ['Route', 'Route Name', 'Vehicle', 'Reg No', 'Driver',
                 'Contact', 'Capacity', 'Riders', 'Stops'],
        'num': [6, 7],
        'rows': rows,
        'foot': None,
        'summary': [
            box('Routes', qs.count(), *BLUE),
            box('Capacity', cap, *PURPLE),
            box('Riders', used, *GREEN),
            box('Free Seats', max(cap - used, 0), *AMBER),
        ],
    }


def r_occupancy(P, cls, term, route):
    rows, cap, used = [], 0, 0

    for v in Vehicle.objects.select_related('driver').prefetch_related('routes').order_by('code'):
        u = v.used_seats
        cap += v.capacity
        used += u
        pct = v.occupancy_percent
        rt = v.routes.first()

        rows.append([
            v.code, v.reg_no,
            f'{rt.code} {rt.name}' if rt else '—',
            v.driver.name if v.driver else '—',
            v.capacity, u, max(v.capacity - u, 0),
            tag(f'{pct}%', 't-red' if pct >= 90 else 't-amber' if pct >= 70 else 't-green'),
        ])

    rate = round(used / cap * 100) if cap else 0

    return {
        'cols': ['Vehicle', 'Reg No', 'Route', 'Driver', 'Capacity', 'Used', 'Free', 'Occupancy'],
        'num': [4, 5, 6],
        'rows': rows,
        'foot': ['TOTAL FLEET', '', '', '', cap, used,
                 max(cap - used, 0), f'{rate}%'] if rows else None,
        'summary': [
            box('Vehicles', len(rows), *BLUE),
            box('Capacity', cap, *PURPLE),
            box('Occupied', used, *GREEN),
            box('Utilization', f'{rate}%', *AMBER),
        ],
    }


def r_strength(P, cls, term, route):
    agg = (CoreStudent.objects.filter(is_active=True)
           .values('student_class')
           .annotate(
               total=Count('id'),
               boys=Count('id', filter=Q(gender__iexact='Male')),
               girls=Count('id', filter=Q(gender__iexact='Female')),
           ).order_by('student_class'))

    rows, T = [], dict(t=0, b=0, g=0, s=0)
    for a in agg:
        c = a['student_class'] or '—'
        secs = ClassDefination.objects.filter(class_field__iexact=c).count() or 1
        T['t'] += a['total']; T['b'] += a['boys']
        T['g'] += a['girls']; T['s'] += secs

        rows.append([c, a['total'], a['boys'], a['girls'], secs,
                     round(a['total'] / secs)])

    return {
        'cols': ['Class', 'Total', 'Boys', 'Girls', 'Sections', 'Avg / Section'],
        'num': [1, 2, 3, 4, 5],
        'rows': rows,
        'foot': ['TOTAL', T['t'], T['b'], T['g'], T['s'], ''] if rows else None,
        'summary': [
            box('Classes', len(rows), *BLUE),
            box('Students', T['t'], *GREEN),
            box('Boys', T['b'], *PURPLE),
            box('Girls', T['g'], *AMBER),
        ],
    }


def r_directory(P, cls, term, route):
    qs = CoreStudent.objects.filter(is_active=True)
    if cls:
        qs = qs.filter(student_class__iexact=cls)

    classes_count = qs.values('student_class').distinct().count()
    qs = qs.order_by('student_class', 'roll_no')[:800]

    rows, m, f = [], 0, 0
    for s in qs:
        g = (s.gender or '').lower()
        if g == 'male':
            m += 1
        elif g == 'female':
            f += 1

        rows.append([
            s.roll_no or '—',
            s.name,
            s.father_name or '—',
            s.student_class or '—',
            s.gender or '—',
            _fmt(s.dob),
            s.contact or '—',
            (s.address or '—')[:48],
        ])

    return {
        'cols': ['Roll No', 'Student Name', 'Father Name', 'Class',
                 'Gender', 'Date of Birth', 'Contact', 'Address'],
        'num': [],
        'rows': rows,
        'foot': None,
        'summary': [
            box('Records', len(rows), *BLUE),
            box('Male', m, *GREEN),
            box('Female', f, *PURPLE),
            box('Classes', classes_count, *AMBER),
        ],
    }


BUILDERS = {
    'defaulters': r_defaulters, 'collection': r_collection,
    'challan':    r_challan,    'daily':      r_daily,
    'result':     r_result,     'subject':    r_subject,
    'salary':     r_salary,     'pending':    r_pending,
    'manifest':   r_manifest,   'occupancy':  r_occupancy,
    'strength':   r_strength,   'directory':  r_directory,
}
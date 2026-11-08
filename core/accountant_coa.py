from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import IntegrityError
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import AccCoaLevel1, AccCoaLevel2, AccCoaLevel3, AccCoaLevel4, AccGeneralLedger


NATURE_CHOICES = [
    ('ASSET', 'Assets'),
    ('LIAB', 'Liabilities'),
    ('EQUITY', 'Equity'),
    ('INCOME', 'Income'),
    ('EXPENSE', 'Expenses'),
]


# ----------------------------
# ID GENERATORS
# ----------------------------
def next_level1_id():
    last = AccCoaLevel1.objects.order_by('-account_id').values_list('account_id', flat=True).first()
    return "01" if not last else f"{int(last) + 1:02d}"


def next_child_code(parent_code: str, last_child_code: str | None, child_digits: int) -> str:
    if not last_child_code:
        nxt = 1
    else:
        suffix = last_child_code[-child_digits:]
        nxt = int(suffix) + 1
    return f"{parent_code}{nxt:0{child_digits}d}"


def next_level2_id(level1: AccCoaLevel1) -> str:
    last = (AccCoaLevel2.objects
            .filter(level1=level1)
            .order_by('-account_id')
            .values_list('account_id', flat=True)
            .first())
    return next_child_code(level1.account_id, last, 2)


def next_level3_id(level2: AccCoaLevel2) -> str:
    last = (AccCoaLevel3.objects
            .filter(level2=level2)
            .order_by('-account_id')
            .values_list('account_id', flat=True)
            .first())
    return next_child_code(level2.account_id, last, 2)


def refresh_lock_level1(level1: AccCoaLevel1):
    has_l2 = AccCoaLevel2.objects.filter(level1=level1).exists()
    if level1.is_locked != has_l2:
        level1.is_locked = has_l2
        level1.save(update_fields=["is_locked"])


def refresh_lock_level2(level2: AccCoaLevel2):
    has_l3 = AccCoaLevel3.objects.filter(level2=level2).exists()
    if level2.is_locked != has_l3:
        level2.is_locked = has_l3
        level2.save(update_fields=["is_locked"])


def refresh_lock_level3(level3: AccCoaLevel3):
    has_l4 = AccCoaLevel4.objects.filter(level3=level3).exists()
    if level3.is_locked != has_l4:
        level3.is_locked = has_l4
        level3.save(update_fields=["is_locked"])


def infer_level1_nature(name: str) -> str:
    n = (name or "").strip().upper()

    liability_kw = ["LIAB", "PAYABLE", "LOAN", "CREDITOR", "ACCRUED"]
    equity_kw = ["EQUITY", "CAPITAL", "OWNER", "RETAINED EARNING", "DRAWING"]
    income_kw = ["INCOME", "REVENUE", "SALES", "FEE RECEIPT", "EARNING"]
    expense_kw = [
        "EXPENSE", "EXPENDITURE", "COST", "COGS", "SALARY", "SALARIES",
        "WAGES", "UTILITIES", "DEPRECIATION", "RENT", "MAINTENANCE",
    ]

    if any(k in n for k in liability_kw):
        return "LIAB"
    if any(k in n for k in equity_kw):
        return "EQUITY"
    if any(k in n for k in income_kw):
        return "INCOME"
    if any(k in n for k in expense_kw):
        return "EXPENSE"

    return "ASSET"


# ============================================================
# COA LEVEL 1
# ============================================================
def coa_level1(request):
    accounts = AccCoaLevel1.objects.all().order_by('account_id')
    next_id = next_level1_id()
    
    for a in accounts:
        refresh_lock_level1(a)

    if request.method == "POST":
        account_name = (request.POST.get("account_name") or "").strip()
        if not account_name:
            messages.error(request, "Account Name is required.")
            return redirect("coa_level1")

        account_id = next_level1_id()
        nature = infer_level1_nature(account_name)

        try:
            AccCoaLevel1.objects.create(
                account_id=account_id,
                account_name=account_name.upper(),
                nature=nature,
                status="Active",
                is_locked=False,
                created_at=timezone.now(),
            )
            messages.success(request, f"Created Level‑1: {account_id} - {account_name}")
        except IntegrityError:
            messages.error(request, "Duplicate Account ID. Try again.")

        return redirect("coa_level1")

    return render(request, "accountant/coa_level1.html", {
        "accounts": AccCoaLevel1.objects.all().order_by('account_id'),
        "next_id": next_id,
    })

    
def coa_level1_edit(request, pk):
    acc = get_object_or_404(AccCoaLevel1, pk=pk)

    if AccCoaLevel2.objects.filter(level1=acc).exists():
        refresh_lock_level1(acc)
        messages.error(request, f"Cannot edit {acc.account_id}. It has Level‑2 sub-categories.")
        return redirect("coa_level1")

    if request.method == "POST":
        name = (request.POST.get("account_name") or "").strip()
        if not name:
            messages.error(request, "Account Name required.")
            return redirect("coa_level1_edit", pk=pk)

        acc.account_name = name.upper()
        acc.nature = infer_level1_nature(name)
        acc.save(update_fields=["account_name", "nature"])

        messages.success(request, f"Updated: {acc.account_id}")
        return redirect("coa_level1")

    return render(request, "accountant/coa_level1_edit.html", {"acc": acc})


@require_POST
def coa_level1_delete(request, pk):
    acc = get_object_or_404(AccCoaLevel1, pk=pk)

    if AccCoaLevel2.objects.filter(level1=acc).exists():
        refresh_lock_level1(acc)
        messages.error(request, f"Cannot delete {acc.account_id}. Delete its Level‑2 sub-categories first.")
        return redirect("coa_level1")

    acc.delete()
    messages.success(request, f"Deleted: {acc.account_id}")
    return redirect("coa_level1")


# ============================================================
# COA LEVEL 2
# ============================================================
def coa_level2(request):
    level1_id = request.GET.get("level1")
    level1_list = AccCoaLevel1.objects.all().order_by("account_id")

    selected_level1 = None
    accounts = AccCoaLevel2.objects.select_related("level1").order_by("account_id")
    next_id = None

    if level1_id:
        selected_level1 = get_object_or_404(AccCoaLevel1, pk=level1_id)
        accounts = accounts.filter(level1=selected_level1)
        next_id = next_level2_id(selected_level1)

    if request.method == "POST":
        parent_id = request.POST.get("level1_id")
        name = (request.POST.get("account_name") or "").strip()

        if not parent_id:
            messages.error(request, "Select Level-1 parent.")
            return redirect("coa_level2")

        parent = get_object_or_404(AccCoaLevel1, pk=parent_id)

        if not name:
            messages.error(request, "Account Name required.")
            return redirect(f"/accountant/coa/level2/?level1={parent_id}")

        new_code = next_level2_id(parent)

        try:
            AccCoaLevel2.objects.create(
                level1=parent,
                account_id=new_code,
                account_name=name.upper(),
                status="Active",
                is_locked=False,
                created_at=timezone.now(),
            )

            refresh_lock_level1(parent)
            messages.success(request, f"Created Level-2: {new_code} - {name}")
            return redirect(f"/accountant/coa/level2/?level1={parent_id}")

        except IntegrityError:
            messages.error(request, "Duplicate Level-2 Account ID. Try again.")
            return redirect(f"/accountant/coa/level2/?level1={parent_id}")

    return render(request, "accountant/coa_level2.html", {
        "level1_list": level1_list,
        "selected_level1": selected_level1,
        "accounts": accounts,
        "next_id": next_id,
    })


def coa_level2_edit(request, pk):
    acc = get_object_or_404(AccCoaLevel2, pk=pk)

    if AccCoaLevel3.objects.filter(level2=acc).exists():
        refresh_lock_level2(acc)
        messages.error(request, f"Cannot edit {acc.account_id}. It has Level‑3 sub-categories.")
        return redirect(f"/accountant/coa/level2/?level1={acc.level1_id}")

    if request.method == "POST":
        name = (request.POST.get("account_name") or "").strip()
        if not name:
            messages.error(request, "Name required.")
            return redirect("coa_level2_edit", pk=pk)

        acc.account_name = name.upper()
        acc.save(update_fields=["account_name"])
        messages.success(request, f"Updated: {acc.account_id}")
        return redirect(f"/accountant/coa/level2/?level1={acc.level1_id}")

    return render(request, "accountant/coa_level2_edit.html", {"acc": acc})


@require_POST
def coa_level2_delete(request, pk):
    acc = get_object_or_404(AccCoaLevel2, pk=pk)

    if AccCoaLevel3.objects.filter(level2=acc).exists():
        refresh_lock_level2(acc)
        messages.error(request, f"Cannot delete {acc.account_id}. Delete its Level‑3 accounts first.")
        return redirect(f"/accountant/coa/level2/?level1={acc.level1_id}")

    parent = acc.level1
    acc.delete()

    refresh_lock_level1(parent)
    messages.success(request, f"Deleted: {acc.account_id}")
    return redirect(f"/accountant/coa/level2/?level1={parent.pk}")


# ============================================================
# COA LEVEL 3
# ============================================================
def coa_level3(request):
    level2_id = request.GET.get('level2')
    selected_level2 = None
    
    # 1. Hamesha SARE level 3 accounts lay aao (Bina kisi filter ke)
    accounts = AccCoaLevel3.objects.all().order_by('account_id')
    
    if level2_id:
        selected_level2 = get_object_or_404(AccCoaLevel2, pk=level2_id)
        # YAHAN SE FILTER REMOVE KAR DIYA HAI TAHA KE BAKI ACCOUNTS GAYAB NA HON
        # accounts = accounts.filter(level2=selected_level2)

    if request.method == "POST":
        account_name = request.POST.get('account_name')
        l2_id = request.POST.get('level2_id')
        l2_obj = get_object_or_404(AccCoaLevel2, pk=l2_id)
        
        new_id = next_level3_id(l2_obj)
        AccCoaLevel3.objects.create(
            account_id=new_id,
            account_name=account_name.upper(),
            level2=l2_obj
        )
        refresh_lock_level2(l2_obj)
        messages.success(request, f"Level-3 Account {new_id} added successfully.")
        return redirect(f'/accountant/coa/level3/?level2={l2_id}')

    level2_list = AccCoaLevel2.objects.all().order_by('account_id')
    next_id = next_level3_id(selected_level2) if selected_level2 else ""

    context = {
        'level2_list': level2_list,
        'selected_level2': selected_level2,
        'accounts': accounts,  # Ab yeh hamesha poori list bhejega
        'next_id': next_id,
    }
    return render(request, 'accountant/coa_level3.html', context)


def coa_level3_edit(request, pk):
    acc = get_object_or_404(AccCoaLevel3, pk=pk)

    if AccCoaLevel4.objects.filter(level3=acc).exists():
        refresh_lock_level3(acc)
        messages.error(request, f"Cannot edit {acc.account_id}. It has Level‑4 accounts under it.")
        return redirect(f"/accountant/coa/level3/?level2={acc.level2_id}")

    if request.method == "POST":
        name = (request.POST.get("account_name") or "").strip()
        if not name:
            messages.error(request, "Account Name is required.")
            return redirect("coa_level3_edit", pk=pk)

        acc.account_name = name.upper()
        acc.save(update_fields=["account_name"])
        messages.success(request, f"Updated: {acc.account_id}")
        return redirect(f"/accountant/coa/level3/?level2={acc.level2_id}")

    return render(request, "accountant/coa_level3_edit.html", {"acc": acc})


@require_POST
def coa_level3_delete(request, pk):
    acc = get_object_or_404(AccCoaLevel3, pk=pk)

    if AccCoaLevel4.objects.filter(level3=acc).exists():
        refresh_lock_level3(acc)
        messages.error(request, f"Cannot delete {acc.account_id}. Delete its Level‑4 accounts first.")
        return redirect(f"/accountant/coa/level3/?level2={acc.level2_id}")

    parent = acc.level2
    acc.delete()

    refresh_lock_level2(parent)
    messages.success(request, f"Deleted: {acc.account_id}")
    return redirect(f"/accountant/coa/level3/?level2={parent.pk}")


# ============================================================
# COA LEVEL 4 (POSTING ACCOUNTS)
# ============================================================

def next_level4_id(level3: AccCoaLevel3) -> str:
    last = (AccCoaLevel4.objects
            .filter(level3=level3)
            .order_by('-account_id')
            .values_list('account_id', flat=True)
            .first())
    return next_child_code(level3.account_id, last, 4)


# ============================================================
# COA LEVEL 4 (POSTING ACCOUNTS)
# ============================================================

def coa_level4(request):
    if request.method == "POST":
        level3_id = request.POST.get('level3_id')
        account_name = request.POST.get('account_name')
        description = request.POST.get('description', '')
        
        is_cash = request.POST.get('is_cash') in ['1', 'on']
        is_bank = request.POST.get('is_bank') in ['1', 'on']
        is_receivable = request.POST.get('is_receivable') in ['1', 'on']
        is_payable = request.POST.get('is_payable') in ['1', 'on']
        is_payable_deposit = request.POST.get('is_payable_deposit') in ['1', 'on'] # Added PD
        
        # --- UNIQUE CONSTRAINTS VERIFICATION (ON ADD) ---
        if is_cash and AccCoaLevel4.objects.filter(is_cash=True).exists():
            messages.error(request, "Cash Account is already Taken by another account!")
            return redirect('coa_level4')
            
        if is_receivable and AccCoaLevel4.objects.filter(is_receivable=True).exists():
            messages.error(request, "Receivable Account is already Taken by another account!")
            return redirect('coa_level4')
            
        if is_payable and AccCoaLevel4.objects.filter(is_payable=True).exists():
            messages.error(request, "Payable Account is already Taken by another account!")
            return redirect('coa_level4')

        if is_payable_deposit and AccCoaLevel4.objects.filter(is_payable_deposit=True).exists():
            messages.error(request, "Payable Deposit Account is already Taken by another account!")
            return redirect('coa_level4')

        allow_cpv = request.POST.get('allow_cpv') == 'on'
        allow_crv = request.POST.get('allow_crv') == 'on'
        allow_bpv = request.POST.get('allow_bpv') == 'on'
        allow_brv = request.POST.get('allow_brv') == 'on'
        allow_jv = request.POST.get('allow_jv') == 'on'

        level3_obj = get_object_or_404(AccCoaLevel3, account_id=level3_id)
        new_id = next_level4_id(level3_obj)

        # accountant_coa.py ke andar coa_level4 function mein yahan change karein:
        level3_obj = get_object_or_404(AccCoaLevel3, account_id=level3_id)
        new_id = next_level4_id(level3_obj)

        AccCoaLevel4.objects.create(
            account_id=new_id,
            account_name=account_name.upper(),
            description=description,
            level3=level3_obj,
            is_cash=is_cash,
            is_bank=is_bank,
            is_receivable=is_receivable,
            is_payable=is_payable,
            is_payable_deposit=is_payable_deposit, 
            allow_cpv=allow_cpv,
            allow_crv=allow_crv,
            allow_bpv=allow_bpv,
            allow_brv=allow_brv,
            allow_jv=allow_jv,
            created_at=timezone.now(),  # <--- Yahan comma lazmi hai
            status='Active'
        )
        
        refresh_lock_level3(level3_obj)
        messages.success(request, f"Level 4 Account '{new_id}' created successfully!")
        return redirect('coa_level4')

    # GET REQUEST DATA (Sending Lock Status to Header)
    cash_taken = AccCoaLevel4.objects.filter(is_cash=True).exists()
    receivable_taken = AccCoaLevel4.objects.filter(is_receivable=True).exists()
    payable_taken = AccCoaLevel4.objects.filter(is_payable=True).exists()
    payable_deposit_taken = AccCoaLevel4.objects.filter(is_payable_deposit=True).exists()

    level3_accounts = AccCoaLevel3.objects.all().order_by('account_id')
    level4_accounts = AccCoaLevel4.objects.all().order_by('account_id')

    for l3 in level3_accounts:
        l3.level1_name = l3.level2.level1.account_name if l3.level2 and l3.level2.level1 else 'Auto'
        l3.level2_name = l3.level2.account_name if l3.level2 else 'Auto'
        l3.next_l4_id = next_level4_id(l3)

    # NAYA CHECK: Har account ke liye dekhein ke ledger mein entries hain ya nahi
    for acc in level4_accounts:
        acc.has_transactions = AccGeneralLedger.objects.filter(account=acc).exists()
        
    context = {
        'cash_taken': cash_taken,
        'receivable_taken': receivable_taken,
        'payable_taken': payable_taken,
        'payable_deposit_taken': payable_deposit_taken,
        'level3_accounts': level3_accounts,
        'level4_accounts': level4_accounts,
    }
    return render(request, 'accountant/coa_level4.html', context)


def coa_level4_edit(request, account_id):
    acc = get_object_or_404(AccCoaLevel4, account_id=account_id)

    if request.method == 'POST':
        # Nayi values lo jo edit form se ayi hain
        new_is_cash = request.POST.get('is_cash') in ['1', 'on']
        new_is_receivable = request.POST.get('is_receivable') in ['1', 'on']
        new_is_payable = request.POST.get('is_payable') in ['1', 'on']
        new_is_payable_deposit = request.POST.get('is_payable_deposit') in ['1', 'on']

        # --- UNIQUE CONSTRAINTS VERIFICATION (ON EDIT) ---
        # Note: .exclude(account_id=acc.account_id) check karta hai ke "Mere ilawa" toh kisi ne nahi liya hua?
        if new_is_cash and AccCoaLevel4.objects.filter(is_cash=True).exclude(account_id=acc.account_id).exists():
            messages.error(request, "Cannot assign Cash type! It is currently locked by another account.")
            return redirect('coa_level4_edit', account_id=account_id)
            
        if new_is_receivable and AccCoaLevel4.objects.filter(is_receivable=True).exclude(account_id=acc.account_id).exists():
            messages.error(request, "Cannot assign Receivable type! It is currently locked by another account.")
            return redirect('coa_level4_edit', account_id=account_id)
            
        if new_is_payable and AccCoaLevel4.objects.filter(is_payable=True).exclude(account_id=acc.account_id).exists():
            messages.error(request, "Cannot assign Payable type! It is currently locked by another account.")
            return redirect('coa_level4_edit', account_id=account_id)

        if new_is_payable_deposit and AccCoaLevel4.objects.filter(is_payable_deposit=True).exclude(account_id=acc.account_id).exists():
            messages.error(request, "Cannot assign Payable Deposit type! It is currently locked by another account.")
            return redirect('coa_level4_edit', account_id=account_id)

        # Agar validations paas ho jayen, toh values update kar do
        acc.account_name = request.POST.get('account_name', '').strip().upper()
        acc.description = request.POST.get('description', '').strip()
        
        acc.is_cash = new_is_cash
        acc.is_bank = request.POST.get('is_bank') in ['1', 'on']
        acc.is_receivable = new_is_receivable
        acc.is_payable = new_is_payable
        acc.is_payable_deposit = new_is_payable_deposit
        
        acc.allow_cpv = request.POST.get('allow_cpv') in ['1', 'on']
        acc.allow_crv = request.POST.get('allow_crv') in ['1', 'on']
        acc.allow_bpv = request.POST.get('allow_bpv') in ['1', 'on']
        acc.allow_brv = request.POST.get('allow_brv') in ['1', 'on']
        acc.allow_jv = request.POST.get('allow_jv') in ['1', 'on']
        
        acc.save()
        messages.success(request, f"Posting account '{acc.account_id}' updated successfully.")
        return redirect('coa_level4')

    return render(request, 'accountant/coa_level4_edit.html', {'acc': acc})

def coa_level4_delete(request, account_id):
    acc = get_object_or_404(AccCoaLevel4, account_id=account_id)
    parent_level3 = acc.level3
    
    try:
        acc.delete()
        refresh_lock_level3(parent_level3)
        messages.success(request, f"Account '{account_id}' removed successfully.")
    except IntegrityError:
        messages.error(
            request, 
            f"Cannot delete account '{acc.account_name}' ({account_id}) because it is tied to existing voucher transactions."
        )
    
    return redirect('coa_level4')
from decimal import Decimal
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.db.models import Q, Sum
from django.contrib import messages
from django.utils import timezone
from .accountant_coa import next_level4_id, refresh_lock_level3
import json
import datetime
from .models import CoreStudent, CoreTeacher

from .models import (
    AccVoucherMaster, 
    AccVoucherDetail, 
    AccCoaLevel1,
    AccCoaLevel2,
    AccCoaLevel3,
    AccCoaLevel4, 
    AccVoucherSequence, 
    AccGeneralLedger, 
    AccBankMaster
)


# def voucher_list(request):
#     """Displays all vouchers (Drafts and Posted)."""
#     vouchers = AccVoucherMaster.objects.all().order_by('-created_at')
#     return render(request, 'accountant/voucher_list.html', {'vouchers': vouchers})


@transaction.atomic
def post_voucher_to_ledger(request, voucher_no):
    """Moves a Draft voucher into the official General Ledger."""
    master = get_object_or_404(AccVoucherMaster, voucher_no=voucher_no)
    
    if master.status == 'Posted':
        messages.warning(request, f"Voucher {voucher_no} is already posted.")
        return redirect('voucher_list')
        
    details = AccVoucherDetail.objects.filter(voucher=master)
    
    for d in details:
        AccGeneralLedger.objects.create(
            voucher=master,
            account=d.account,
            date=master.date,
            debit=d.debit,
            credit=d.credit,
            narration=d.narration,
            created_at=timezone.now()
        )
        
    master.status = 'Posted'
    master.save()
    
    messages.success(request, f"Voucher {voucher_no} successfully posted to the General Ledger!")
    return redirect('voucher_list')


def generate_voucher_no(v_type):
    current_year = str(date.today().year)
    seq, created = AccVoucherSequence.objects.get_or_create(
        voucher_type=v_type, fiscal_year=current_year,
        defaults={'last_sequence': 0}
    )
    seq.last_sequence += 1
    seq.save()
    return f"{v_type}-{current_year}-{seq.last_sequence:04d}"

from django.http import JsonResponse

def voucher_entry(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            v_type = data.get('voucher_type')
            v_date = data.get('voucher_date')
            v_ref = data.get('reference', '')
            rows = data.get('rows', [])

            if not rows or not v_type or not v_date:
                return JsonResponse({'status': 'error', 'message': 'Missing required voucher data.'})

            # Strict Backend Validation
            total_dr = sum(Decimal(str(r.get('dr', '0.00'))) for r in rows)
            total_cr = sum(Decimal(str(r.get('cr', '0.00'))) for r in rows)

            if total_dr != total_cr or total_dr <= Decimal('0.00'):
                return JsonResponse({'status': 'error', 'message': f'Total Debit ({total_dr}) and Total Credit ({total_cr}) must match!'})

            # Generate Uniform Unique Voucher No using Full Year (e.g., CPV-2026-0001)
            date_obj = timezone.datetime.strptime(v_date, '%Y-%m-%d')
            year_str = date_obj.strftime('%Y') # Full Year: 2026
            prefix = f"{v_type}-{year_str}-"
            
            # Database check kar ke next sequence nikalna
            last_voucher = AccVoucherMaster.objects.filter(voucher_no__startswith=prefix).order_by('-voucher_no').first()
            if last_voucher:
                last_seq = int(last_voucher.voucher_no.split('-')[-1])
                next_seq = last_seq + 1
            else:
                next_seq = 1
            
            voucher_no = f"{prefix}{next_seq:04d}"

            with transaction.atomic():
                # THE FIX: Database columns ke exact names use kiye hain (date, description, created_at)
                master = AccVoucherMaster.objects.create(
                    voucher_no=voucher_no,
                    voucher_type=v_type,
                    date=v_date,                # Corrected
                    description=v_ref,          # Corrected
                    status='Draft',
                    total_amount=total_dr,
                    created_at=timezone.now()   # Added exact field
                )

                for r in rows:
                    account = AccCoaLevel4.objects.get(account_id=r['accId'])
                    AccVoucherDetail.objects.create(
                        voucher=master,
                        account=account,
                        narration=r.get('narration', ''),
                        debit=Decimal(str(r.get('dr', '0.00'))),
                        credit=Decimal(str(r.get('cr', '0.00')))
                    )
            
            return JsonResponse({'status': 'success', 'voucher_no': voucher_no, 'message': 'Voucher saved successfully!'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    # ==========================================
    # GET Request Logic (Pehle wala hi rahega)
    # ==========================================
    
    accounts = AccCoaLevel4.objects.filter(status='Active').values(
        'account_id', 'account_name', 
        'allow_cpv', 'allow_crv', 'allow_bpv', 'allow_brv', 'is_cash', 'is_bank'
    )
    accounts_json = json.dumps(list(accounts))

    # Single Cash account fetch karein (Kyunke cash aik hi hota hai)
    cash_acc = AccCoaLevel4.objects.filter(is_cash=True, status='Active').first()
    
    # Sare active Bank accounts ki list fetch karein (Kyunke multiple banks ho sakte hain)
    bank_accounts = list(AccCoaLevel4.objects.filter(is_bank=True, status='Active').values('account_id', 'account_name'))
    bank_accounts_json = json.dumps(bank_accounts)

    master_accounts = {
        'cash_id': cash_acc.account_id if cash_acc else '',
        'cash_name': cash_acc.account_name if cash_acc else 'Cash Account Not Set',
    }
    master_accounts_json = json.dumps(master_accounts)

    context = {
        'accounts_json': accounts_json,
        'master_accounts_json': master_accounts_json,
        'bank_accounts_json': bank_accounts_json, # <--- Added multiple banks list
        'current_date': timezone.now().strftime('%Y-%m-%d'),
    }
    return render(request, 'accountant/voucher_entry.html', context)
            
def general_ledger_report(request):
    search_query = request.GET.get('q', '').strip()
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    
    today = datetime.date.today()
    if not from_date:
        from_date = f"{today.year}-01-01"
    if not to_date:
        to_date = today.strftime('%Y-%m-%d')

    entries = []
    opening_balance = Decimal('0.00')
    total_debit = Decimal('0.00')
    total_credit = Decimal('0.00')
    selected_account = None

    if search_query:
        # 1. Find account in Chart of Accounts (Level 4)
        selected_account = AccCoaLevel4.objects.filter(
            Q(account_id__icontains=search_query) | 
            Q(account_name__icontains=search_query)
        ).first()

        if selected_account:
            # Check if this account has an opening balance in AccBankMaster
            bank_master = AccBankMaster.objects.filter(account=selected_account).first()
            bank_opening = bank_master.opening_balance if bank_master and bank_master.opening_balance else Decimal('0.00')

            # 2. Get Ledger Entries within date range
            qs = AccGeneralLedger.objects.filter(
                account=selected_account,
                date__range=[from_date, to_date]
            ).order_by('date', 'id')

            # 3. Calculate Opening Balance (transactions before from_date + Bank Master opening balance)
            prior_entries = AccGeneralLedger.objects.filter(
                account=selected_account,
                date__lt=from_date
            )
            prior_dr = prior_entries.aggregate(Sum('debit'))['debit__sum'] or Decimal('0.00')
            prior_cr = prior_entries.aggregate(Sum('credit'))['credit__sum'] or Decimal('0.00')
            
            # Total Opening Balance = Bank Master Opening + Prior Debit - Prior Credit
            opening_balance = bank_opening + (prior_dr - prior_cr)

            running_bal = opening_balance
            for entry in qs:
                running_bal += (entry.debit - entry.credit)
                total_debit += entry.debit
                total_credit += entry.credit
                entries.append({
                    'date': entry.date,
                    'voucher_no': entry.voucher.voucher_no,
                    'narration': entry.narration,
                    'debit': entry.debit,
                    'credit': entry.credit,
                    'balance': running_bal
                })

    closing_balance = opening_balance + total_debit - total_credit

    # Fetch all active Level 4 accounts for the searchable dropdown
    all_accounts = AccCoaLevel4.objects.filter(status='Active').order_by('account_id')

    context = {
        'search_query': search_query,
        'from_date': from_date,
        'to_date': to_date,
        'selected_account': selected_account,
        'opening_balance': opening_balance,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'closing_balance': closing_balance,
        'entries': entries,
        'all_accounts': all_accounts,
    }
    return render(request, 'accountant/general_ledger.html', context)   
   
def trial_balance_report(request):
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    hide_zero = request.GET.get('hide_zero') == 'on'
    level_filter = request.GET.get('level', '').strip()
    head_code = request.GET.get('head_code', '').strip()

    today = datetime.date.today()
    if not from_date:
        from_date = f"{today.year}-01-01"
    if not to_date:
        to_date = today.strftime('%Y-%m-%d')

    tb_rows = []
    total_closing_dr = Decimal('0.00')
    total_closing_cr = Decimal('0.00')

    # Helper function to compute balances for a set of Level 4 accounts
    def calculate_node_balances(l4_qs):
        op_dr = Decimal('0.00')
        op_cr = Decimal('0.00')
        per_dr = Decimal('0.00')
        per_cr = Decimal('0.00')
        cl_dr = Decimal('0.00')
        cl_cr = Decimal('0.00')

        has_activity = False

        for acc in l4_qs:
            # 1. Bank opening balance if applicable
            bank_master = AccBankMaster.objects.filter(account=acc).first()
            bank_opening = bank_master.opening_balance if bank_master and bank_master.opening_balance else Decimal('0.00')

            # 2. Prior entries (Before from_date)
            prior_entries = AccGeneralLedger.objects.filter(account=acc, date__lt=from_date)
            prior_dr = prior_entries.aggregate(Sum('debit'))['debit__sum'] or Decimal('0.00')
            prior_cr = prior_entries.aggregate(Sum('credit'))['credit__sum'] or Decimal('0.00')

            net_opening = bank_opening + (prior_dr - prior_cr)
            if net_opening > 0:
                op_dr += net_opening
            elif net_opening < 0:
                op_cr += abs(net_opening)

            # 3. Period entries (Between from_date and to_date)
            period_entries = AccGeneralLedger.objects.filter(account=acc, date__range=[from_date, to_date])
            p_dr = period_entries.aggregate(Sum('debit'))['debit__sum'] or Decimal('0.00')
            p_cr = period_entries.aggregate(Sum('credit'))['credit__sum'] or Decimal('0.00')

            per_dr += p_dr
            per_cr += p_cr

            if net_opening != 0 or p_dr != 0 or p_cr != 0 or bank_opening != 0:
                has_activity = True

        # 4. Closing balance calculation
        net_closing = (op_dr - op_cr) + (per_dr - per_cr)
        if net_closing > 0:
            cl_dr = net_closing
        elif net_closing < 0:
            cl_cr = abs(net_closing)

        return op_dr, op_cr, per_dr, per_cr, cl_dr, cl_cr, has_activity

    # Select level objects based on filter
    if level_filter == 'First Level':
        nodes = AccCoaLevel1.objects.all()
        if head_code:
            nodes = nodes.filter(account_id__startswith=head_code)
        nodes = nodes.order_by('account_id')

        for node in nodes:
            l4_qs = AccCoaLevel4.objects.filter(level3__level2__level1=node)
            op_dr, op_cr, per_dr, per_cr, cl_dr, cl_cr, active = calculate_node_balances(l4_qs)
            if hide_zero and not active and cl_dr == 0 and cl_cr == 0:
                continue
            total_closing_dr += cl_dr
            total_closing_cr += cl_cr
            tb_rows.append({
                'account_id': node.account_id,
                'account_name': node.account_name,
                'opening_dr': op_dr,
                'opening_cr': op_cr,
                'period_dr': per_dr,
                'period_cr': per_cr,
                'closing_dr': cl_dr,
                'closing_cr': cl_cr,
            })

    elif level_filter == 'Second Level':
        nodes = AccCoaLevel2.objects.all()
        if head_code:
            nodes = nodes.filter(account_id__startswith=head_code)
        nodes = nodes.order_by('account_id')

        for node in nodes:
            l4_qs = AccCoaLevel4.objects.filter(level3__level2=node)
            op_dr, op_cr, per_dr, per_cr, cl_dr, cl_cr, active = calculate_node_balances(l4_qs)
            if hide_zero and not active and cl_dr == 0 and cl_cr == 0:
                continue
            total_closing_dr += cl_dr
            total_closing_cr += cl_cr
            tb_rows.append({
                'account_id': node.account_id,
                'account_name': node.account_name,
                'opening_dr': op_dr,
                'opening_cr': op_cr,
                'period_dr': per_dr,
                'period_cr': per_cr,
                'closing_dr': cl_dr,
                'closing_cr': cl_cr,
            })

    elif level_filter == 'Third Level':
        nodes = AccCoaLevel3.objects.all()
        if head_code:
            nodes = nodes.filter(account_id__startswith=head_code)
        nodes = nodes.order_by('account_id')

        for node in nodes:
            l4_qs = AccCoaLevel4.objects.filter(level3=node)
            op_dr, op_cr, per_dr, per_cr, cl_dr, cl_cr, active = calculate_node_balances(l4_qs)
            if hide_zero and not active and cl_dr == 0 and cl_cr == 0:
                continue
            total_closing_dr += cl_dr
            total_closing_cr += cl_cr
            tb_rows.append({
                'account_id': node.account_id,
                'account_name': node.account_name,
                'opening_dr': op_dr,
                'opening_cr': op_cr,
                'period_dr': per_dr,
                'period_cr': per_cr,
                'closing_dr': cl_dr,
                'closing_cr': cl_cr,
            })

    else:
        # Fourth Level (Posting Accounts) or All Levels
        nodes = AccCoaLevel4.objects.all()
        if head_code:
            nodes = nodes.filter(account_id__startswith=head_code)
        nodes = nodes.order_by('account_id')

        for node in nodes:
            op_dr, op_cr, per_dr, per_cr, cl_dr, cl_cr, active = calculate_node_balances([node])
            if hide_zero and not active and cl_dr == 0 and cl_cr == 0:
                continue
            total_closing_dr += cl_dr
            total_closing_cr += cl_cr
            tb_rows.append({
                'account_id': node.account_id,
                'account_name': node.account_name,
                'opening_dr': op_dr,
                'opening_cr': op_cr,
                'period_dr': per_dr,
                'period_cr': per_cr,
                'closing_dr': cl_dr,
                'closing_cr': cl_cr,
            })

    total_opening_dr = sum(r['opening_dr'] for r in tb_rows)
    total_opening_cr = sum(r['opening_cr'] for r in tb_rows)
    total_period_dr = sum(r['period_dr'] for r in tb_rows)
    total_period_cr = sum(r['period_cr'] for r in tb_rows)

    is_balanced = (total_closing_dr == total_closing_cr)

    context = {
        'tb_rows': tb_rows,
        'from_date': from_date,
        'to_date': to_date,
        'hide_zero': hide_zero,
        'level_filter': level_filter,
        'head_code': head_code,
        'total_rows': len(tb_rows),
        'total_closing_dr': total_closing_dr,
        'total_closing_cr': total_closing_cr,
        'total_opening_dr': total_opening_dr,
        'total_opening_cr': total_opening_cr,
        'total_period_dr': total_period_dr,
        'total_period_cr': total_period_cr,
        'is_balanced': is_balanced,
    }
    return render(request, 'accountant/trial_balance.html', context)
 
        
def bank_file_view(request):
    if request.method == "POST":
        level3_id = request.POST.get('level3_id')
        bank_name = request.POST.get('bank_name')
        account_title = request.POST.get('account_title')
        account_number = request.POST.get('account_number')
        branch_name = request.POST.get('branch_name', '')
        branch_code = request.POST.get('branch_code', '')
        iban = request.POST.get('iban', '')
        swift_code = request.POST.get('swift_code', '')
        opening_balance_val = request.POST.get('opening_balance', '0.00')

        # Strict Decimal conversion for opening balance
        try:
            opening_balance = Decimal(opening_balance_val if opening_balance_val else '0.00')
        except:
            opening_balance = Decimal('0.00')

        # 1. Level 3 Parent find karein
        level3_obj = get_object_or_404(AccCoaLevel3, account_id=level3_id)
        
        # 2. Next Level 4 ID generate karein
        new_l4_id = next_level4_id(level3_obj)

        try:
            with transaction.atomic():
                # A. Pehlay Level 4 Account Create Karein (Strict Bank Rules ke sath)
                bank_account_obj = AccCoaLevel4.objects.create(
                    account_id=new_l4_id,
                    account_name=f"{bank_name} - {account_title}".upper(),
                    description=f"Bank Account: {account_number} ({branch_name})",
                    level3=level3_obj,
                    is_cash=False,
                    is_bank=True,            # Sirf Bank Account hoga
                    is_receivable=False,     # Never Receivable
                    is_payable=False,        # Never Payable
                    is_payable_deposit=False,# Never PD
                    allow_cpv=False,
                    allow_crv=False,
                    allow_bpv=True,          # BPV Strictly Allowed
                    allow_brv=True,          # BRV Strictly Allowed
                    allow_jv=True,           # JV Allowed for adjustments
                    status='Active',
                    created_at=timezone.now()
                )
                refresh_lock_level3(level3_obj)

                # B. Phir usay Bank Master ke sath link kar ke save karein
                AccBankMaster.objects.create(
                    account=bank_account_obj,
                    bank_name=bank_name,
                    account_title=account_title,
                    account_number=account_number,
                    branch_name=branch_name,
                    branch_code=branch_code,
                    iban=iban,
                    swift_code=swift_code,
                    is_active=True,
                    created_at=timezone.now(),
                    opening_balance=opening_balance
                )
            messages.success(request, f"Success! Bank '{bank_name}' created & auto-linked to Level 4 ({new_l4_id}).")
        except Exception as e:
            messages.error(request, f"Error saving bank account: {str(e)}")
            
        return redirect('bank_file')

    # GET Request: Filter ONLY Bank-related Level 3 accounts for selection
    level3_list = AccCoaLevel3.objects.filter(
        Q(account_name__icontains='BANK') | Q(account_id__icontains='BANK')
    ).order_by('account_id')
    
    # Fallback agar koi explicit 'BANK' naam na mila ho taake dropdown khali na ho
    if not level3_list.exists():
        level3_list = AccCoaLevel3.objects.all().order_by('account_id')

    for l3 in level3_list:
        l3.next_l4_id = next_level4_id(l3)

    bank_records = AccBankMaster.objects.select_related('account').all().order_by('-id')

    context = {
        'level3_accounts': level3_list,
        'bank_records': bank_records
    }
    return render(request, 'accountant/bank_file.html', context)


def bank_file_edit(request, bank_id):
    bank_record = get_object_or_404(AccBankMaster, id=bank_id)
    
    if request.method == "POST":
        bank_record.bank_name = request.POST.get('bank_name')
        bank_record.account_title = request.POST.get('account_title')
        bank_record.account_number = request.POST.get('account_number')
        bank_record.branch_name = request.POST.get('branch_name', '')
        bank_record.branch_code = request.POST.get('branch_code', '')
        bank_record.iban = request.POST.get('iban', '')
        bank_record.swift_code = request.POST.get('swift_code', '')
        bank_record.opening_balance = request.POST.get('opening_balance', 0.00)
        bank_record.is_active = 'is_active' in request.POST
        bank_record.save()
        return redirect('bank_file')

    return render(request, 'accountant/bank_file_edit.html', {'bank_record': bank_record})


def bank_file_delete(request, bank_id):
    bank_record = get_object_or_404(AccBankMaster, id=bank_id)
    level4_account = bank_record.account  # Linked Level 4 account
    
    try:
        with transaction.atomic():
            # 1. Pehle Bank Master delete hoga
            bank_record.delete()
            # 2. Uske baad uska linked Level 4 account bhi database se mukammal delete ho jayega
            if level4_account:
                level4_account.delete()
                
        messages.success(request, "Bank account aur iska Level-4 record database se kamiyabi ke sath delete ho gaya hai!")
    except Exception as e:
        messages.error(request, f"Delete karne mein error aa gaya: {str(e)}")
        
    return redirect('bank_file')


# Ensure you have imported AccGeneralLedger at the top of your file

def voucher_register(request):
    """Sare vouchers ki list show karta hai with Total Amount"""
    # Yahan 'total_amount' ko change kar ke 'voucher_total' karna hai
    vouchers = AccVoucherMaster.objects.annotate(
        voucher_total=Sum('accvoucherdetail__debit')
    ).order_by('-voucher_no')
    
    context = {
        'vouchers': vouchers
    }
    return render(request, 'accountant/voucher_register.html', context)

def delete_voucher(request, voucher_no):
    """Draft voucher ko mukammal delete karne ki logic"""
    voucher = get_object_or_404(AccVoucherMaster, voucher_no=voucher_no)
    
    if voucher.status == 'Draft':
        voucher.delete() # Master delete hoga toh Details (rows) khud delete ho jayengi
        messages.success(request, f"Voucher {voucher.voucher_no} has been deleted.")
    else:
        messages.error(request, "You cannot delete a POSTED voucher. Please reverse it via JV instead.")
        
    return redirect('voucher_register')

def post_voucher(request, voucher_no):
    """Draft voucher ko Post kar ke General Ledger me push karna"""
    voucher = get_object_or_404(AccVoucherMaster, voucher_no=voucher_no)
    
    if voucher.status == 'Draft':
        try:
            with transaction.atomic():
                # 1. Status ko 'Posted' kar do
                voucher.status = 'Posted'
                voucher.save()
                
                # 2. General Ledger mein entries push karo
                details = AccVoucherDetail.objects.filter(voucher=voucher)
                for d in details:
                    AccGeneralLedger.objects.create(
                        voucher=voucher,
                        account=d.account,
                        date=voucher.date,        # Corrected column mapping
                        narration=d.narration,    # Corrected column mapping
                        debit=d.debit,
                        credit=d.credit,
                        created_at=timezone.now()
                    )
            messages.success(request, f"Voucher {voucher.voucher_no} successfully POSTED to Ledger!")
        except Exception as e:
            messages.error(request, f"Error posting voucher: {str(e)}")
    else:
        messages.error(request, "Voucher is already posted.")
        
    return redirect('voucher_register')

def journal_voucher_view(request):
    """Renders the dedicated Journal Voucher (JV) interface."""
    today = timezone.now().strftime('%Y-%m-%d')
    
    # Next JV Voucher No calculate karne ke liye
    current_year = str(date.today().year)
    seq, created = AccVoucherSequence.objects.get_or_create(
        voucher_type='JV', fiscal_year=current_year,
        defaults={'last_sequence': 0}
    )
    next_seq = seq.last_sequence + 1
    next_voucher_no = f"JV-{current_year}-{next_seq:04d}"

    # NEW: Fetch active accounts where JV is allowed
    accounts = AccCoaLevel4.objects.filter(status='Active', allow_jv=True).values(
        'account_id', 'account_name'
    )
    accounts_json = json.dumps(list(accounts))

    context = {
        'today': today,
        'next_voucher_no': next_voucher_no,
        'accounts_json': accounts_json, # Add this to context
    }
    return render(request, 'accountant/journal_voucher.html', context)




def submit_journal_voucher(request):
    if request.method == "POST":
        date = request.POST.get('date')
        ref_no = request.POST.get('ref_no', '')
        description = request.POST.get('description', '')
        
        # Frontend se accounts, debits, credits ki lists ya JSON aayegi
        account_ids = request.POST.getlist('account_id[]')
        debits = request.POST.getlist('debit[]')
        credits = request.POST.getlist('credit[]')
        narrations = request.POST.getlist('narration[]')

        try:
            # 1. Total Debit aur Credit ka balance check karein
            total_dr = sum(Decimal(d or '0.00') for d in debits)
            total_cr = sum(Decimal(c or '0.00') for c in credits)

            if total_dr != total_cr or total_dr <= Decimal('0.00'):
                messages.error(request, "Error: Debit aur Credit totals barabar honay chahiyein!")
                return redirect('voucher_entry')

            # 2. Fiscal Year calculate karein
            voucher_date = timezone.datetime.strptime(date, '%Y-%m-%d').date()
            fiscal_year = f"{voucher_date.year}-{voucher_date.year+1}" if voucher_date.month >= 7 else f"{voucher_date.year-1}-{voucher_date.year}"

            # 3. Unique Voucher Number Generate Karein (JV format)
            seq, created = AccVoucherSequence.objects.get_or_create(
                voucher_type='JV',
                fiscal_year=fiscal_year,
                defaults={'last_sequence': 0}
            )
            seq.last_sequence += 1
            seq.save()
            voucher_no = f"JV-{fiscal_year}-{seq.last_sequence:05d}"

            # 4. Voucher Master Create Karein
            voucher_master = AccVoucherMaster.objects.create(
                voucher_no=voucher_no,
                voucher_type='JV',
                date=voucher_date,
                description=description or ref_no,
                status='Posted',
                total_amount=total_dr,
                created_at=timezone.now()
            )

            # 5. Voucher Details aur General Ledger Entries Loop mein save karein
            for acc_id, dr, cr, narr in zip(account_ids, debits, credits, narrations):
                if not acc_id:
                    continue
                account_obj = AccCoaLevel4.objects.get(account_id=acc_id)
                dr_val = Decimal(dr or '0.00')
                cr_val = Decimal(cr or '0.00')
                line_narration = narr or description

                # Voucher Detail
                AccVoucherDetail.objects.create(
                    voucher=voucher_master,
                    account=account_obj,
                    debit=dr_val,
                    credit=cr_val,
                    narration=line_narration
                )

                # General Ledger mein direct posting
                AccGeneralLedger.objects.create(
                    voucher=voucher_master,
                    account=account_obj,
                    date=voucher_date,
                    debit=dr_val,
                    credit=cr_val,
                    narration=line_narration,
                    created_at=timezone.now()
                )

            messages.success(request, f"Journal Voucher {voucher_no} kamiyabi ke sath post ho gaya hai!")
            return redirect('voucher_entry')

        except Exception as e:
            messages.error(request, f"Voucher posting mein error aa gaya: {e}")
            return redirect('voucher_entry')

    return redirect('voucher_entry')

def print_voucher(request, voucher_no):
    """Specific voucher ki details fetch kar ke print layout render karta hai"""
    master = get_object_or_404(AccVoucherMaster, voucher_no=voucher_no)
    details = AccVoucherDetail.objects.filter(voucher=master).select_related('account')
    
    context = {
        'master': master,
        'details': details,
        'school_name': 'ACERO GRAMMAR SCHOOL',
        'school_address': 'Main Campus, Sialkot',
    }
    return render(request, 'accountant/print_voucher.html', context)
# core/accountant_posting_config.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone

from .models import AccCoaLevel4, AccSchoolPostingConfig


# ------------------------------------------------------------
# Fixed set of posting slots the rest of the Accountant module
# (and later, the Accounts/Payroll auto-posting integration)
# will look up by config_key. Add new slots here only.
# ------------------------------------------------------------
POSTING_CONFIG_KEYS = [
    ("FEE_CASH", "Fee Collection — Cash Account",
     "Debited when a student fee is paid in cash (Cash Receipt Voucher)."),
    ("FEE_BANK", "Fee Collection — Bank Account",
     "Debited when a student fee is paid via bank/online transfer (Bank Receipt Voucher)."),
    ("INCOME_TUITION", "Tuition Fee Income Account",
     "Credited when tuition fee is collected."),
    ("INCOME_TRANSPORT", "Transport Fee Income Account",
     "Credited when transport fee is collected."),
    ("INCOME_OTHER", "Other / Misc Income Account",
     "Credited for admission fee, fines, and other miscellaneous income."),
    ("SALARY_EXPENSE", "Salary Expense Account",
     "Debited when a payroll disbursement is posted."),
    ("SALARY_PAYABLE", "Salary Payable Account",
     "Credited when a payroll amount is accrued but not yet paid out."),
]

_VALID_KEYS = {key for key, _, _ in POSTING_CONFIG_KEYS}


def _account_flag_tags(acc):
    """Small hint tags shown next to each dropdown option so the admin
    can tell which Level-4 accounts were flagged Cash/Bank/Receivable/Payable
    when they were created, without enforcing a hard filter."""
    tags = []
    if acc.is_cash:
        tags.append("CASH")
    if acc.is_bank:
        tags.append("BANK")
    if acc.is_receivable:
        tags.append("REC")
    if acc.is_payable:
        tags.append("PAY")
    return tags


def posting_config(request):
    accounts = list(
        AccCoaLevel4.objects.filter(status="Active").order_by("account_id")
    )
    for a in accounts:
        a.flag_tags = _account_flag_tags(a)

    if request.method == "POST":
        for key, label, _hint in POSTING_CONFIG_KEYS:
            account_id = (request.POST.get(key) or "").strip()
            account_obj = None

            if account_id:
                account_obj = AccCoaLevel4.objects.filter(account_id=account_id).first()
                if not account_obj:
                    messages.error(request, f"Invalid account selected for '{label}'.")
                    return redirect("posting_config")

            AccSchoolPostingConfig.objects.update_or_create(
                config_key=key,
                defaults={
                    "config_name": label,
                    "account": account_obj,
                    "updated_at": timezone.now(),
                },
            )

        messages.success(request, "Posting configuration saved.")
        return redirect("posting_config")

    existing = {
        row.config_key: row
        for row in AccSchoolPostingConfig.objects.filter(config_key__in=_VALID_KEYS)
    }

    rows = []
    for key, label, hint in POSTING_CONFIG_KEYS:
        current = existing.get(key)
        rows.append({
            "key": key,
            "label": label,
            "hint": hint,
            "current_account": current.account if current else None,
        })

    return render(request, "accountant/posting_config.html", {
        "rows": rows,
        "accounts": accounts,
    })
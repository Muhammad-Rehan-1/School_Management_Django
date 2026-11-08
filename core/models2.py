# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AuditUserSession(models.Model):
    spid = models.IntegerField(primary_key=True)
    user_id = models.IntegerField(blank=True, null=True)
    user_name = models.CharField(max_length=120, blank=True, null=True)
    user_role = models.CharField(max_length=50, blank=True, null=True)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    logged_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'Audit_User_Session'


class ClassDefination(models.Model):
    class_field = models.CharField(db_column='class', max_length=50)  # Field renamed because it was a Python reserved word.
    section = models.CharField(max_length=50)
    room_number = models.CharField(max_length=50)
    max_capacity = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    created_at = models.DateField()

    class Meta:
        managed = False
        db_table = 'Class_defination'


class ClassDefinationLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField()
    class_field = models.CharField(db_column='class', max_length=50, blank=True, null=True)  # Field renamed because it was a Python reserved word.
    section = models.CharField(max_length=50, blank=True, null=True)
    room_number = models.CharField(max_length=50, blank=True, null=True)
    max_capacity = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Class_defination_log'


class SchoolProfile(models.Model):
    school_name = models.CharField(max_length=200)
    campus_name = models.CharField(max_length=200, blank=True, null=True)
    registration_no = models.CharField(max_length=100, blank=True, null=True)
    board_affiliation = models.CharField(max_length=200, blank=True, null=True)
    address = models.CharField(max_length=500, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=254, blank=True, null=True)
    is_active = models.BooleanField()
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'School_Profile'


class SchoolProfileLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    school_name = models.CharField(max_length=200, blank=True, null=True)
    campus_name = models.CharField(max_length=200, blank=True, null=True)
    registration_no = models.CharField(max_length=100, blank=True, null=True)
    board_affiliation = models.CharField(max_length=200, blank=True, null=True)
    address = models.CharField(max_length=500, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=254, blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'School_Profile_log'


class SubjectDefination(models.Model):
    subject_name = models.CharField(max_length=100)
    subject_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    created_date = models.DateField()

    class Meta:
        managed = False
        db_table = 'Subject_Defination'


class SubjectDefinationLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField()
    subject_name = models.CharField(max_length=100, blank=True, null=True)
    subject_type = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=100, blank=True, null=True)
    created_date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Subject_Defination_log'


class TimetableDay(models.Model):
    day_of_week = models.SmallIntegerField(unique=True)
    name = models.CharField(max_length=10)
    is_working = models.BooleanField()
    last_period_no = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Timetable_Day'


class TimetableDayLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    day_of_week = models.SmallIntegerField(blank=True, null=True)
    name = models.CharField(max_length=10, blank=True, null=True)
    is_working = models.BooleanField(blank=True, null=True)
    last_period_no = models.IntegerField(blank=True, null=True)
    id = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Timetable_Day_log'


class TimetablePeriod(models.Model):
    sort_order = models.IntegerField(unique=True)
    period_no = models.IntegerField(unique=True, blank=True, null=True)
    name = models.CharField(max_length=50)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_break = models.BooleanField()
    is_active = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'Timetable_Period'


class TimetablePeriodLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    sort_order = models.IntegerField(blank=True, null=True)
    period_no = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    is_break = models.BooleanField(blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)
    id = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Timetable_Period_log'


class TimetableSlot(models.Model):
    session = models.CharField(max_length=20)
    class_field = models.CharField(db_column='class', max_length=50)  # Field renamed because it was a Python reserved word.
    section = models.CharField(max_length=50)
    day_of_week = models.SmallIntegerField()
    period_no = models.IntegerField()
    subject = models.CharField(max_length=100)
    emp_id = models.CharField(max_length=50, blank=True, null=True)
    room = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Timetable_Slot'
        unique_together = (('session', 'class_field', 'section', 'day_of_week', 'period_no'),)


class TimetableSlotLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    session = models.CharField(max_length=20, blank=True, null=True)
    class_field = models.CharField(db_column='class', max_length=50, blank=True, null=True)  # Field renamed because it was a Python reserved word.
    section = models.CharField(max_length=50, blank=True, null=True)
    day_of_week = models.SmallIntegerField(blank=True, null=True)
    period_no = models.IntegerField(blank=True, null=True)
    subject = models.CharField(max_length=100, blank=True, null=True)
    emp_id = models.CharField(max_length=50, blank=True, null=True)
    room = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    id = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Timetable_Slot_log'


class AcademicSession(models.Model):
    session_name = models.CharField(unique=True, max_length=50)
    is_current = models.BooleanField()
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'academic_session'


class AcademicSessionLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    session_name = models.CharField(max_length=50, blank=True, null=True)
    is_current = models.BooleanField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'academic_session_log'


class AccBankMaster(models.Model):
    account_id = models.CharField(unique=True, max_length=12)
    bank_name = models.CharField(max_length=150)
    branch_name = models.CharField(max_length=100, blank=True, null=True)
    branch_code = models.CharField(max_length=20, blank=True, null=True)
    account_title = models.CharField(max_length=150)
    account_number = models.CharField(max_length=100)
    iban = models.CharField(max_length=50, blank=True, null=True)
    swift_code = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField()
    created_at = models.DateTimeField()
    opening_balance = models.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'acc_bank_master'


class AccBankMasterLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    account_id = models.CharField(max_length=12, blank=True, null=True)
    bank_name = models.CharField(max_length=150, blank=True, null=True)
    branch_name = models.CharField(max_length=100, blank=True, null=True)
    branch_code = models.CharField(max_length=20, blank=True, null=True)
    account_title = models.CharField(max_length=150, blank=True, null=True)
    account_number = models.CharField(max_length=100, blank=True, null=True)
    iban = models.CharField(max_length=50, blank=True, null=True)
    swift_code = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    opening_balance = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'acc_bank_master_log'


class AccCoaLevel1(models.Model):
    account_id = models.CharField(unique=True, max_length=2)
    account_name = models.CharField(max_length=100)
    nature = models.CharField(max_length=10)
    is_locked = models.BooleanField()
    status = models.CharField(max_length=10)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'acc_coa_level1'


class AccCoaLevel1Log(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    account_id = models.CharField(max_length=2, blank=True, null=True)
    account_name = models.CharField(max_length=100, blank=True, null=True)
    nature = models.CharField(max_length=10, blank=True, null=True)
    is_locked = models.BooleanField(blank=True, null=True)
    status = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'acc_coa_level1_log'


class AccCoaLevel2(models.Model):
    level1 = models.ForeignKey(AccCoaLevel1, models.DO_NOTHING)
    account_id = models.CharField(unique=True, max_length=4)
    account_name = models.CharField(max_length=100)
    is_locked = models.BooleanField()
    status = models.CharField(max_length=10)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'acc_coa_level2'


class AccCoaLevel2Log(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    level1_id = models.IntegerField(blank=True, null=True)
    account_id = models.CharField(max_length=4, blank=True, null=True)
    account_name = models.CharField(max_length=100, blank=True, null=True)
    is_locked = models.BooleanField(blank=True, null=True)
    status = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'acc_coa_level2_log'


class AccCoaLevel3(models.Model):
    level2 = models.ForeignKey(AccCoaLevel2, models.DO_NOTHING)
    account_id = models.CharField(unique=True, max_length=6)
    account_name = models.CharField(max_length=120)
    is_locked = models.BooleanField()
    status = models.CharField(max_length=10)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'acc_coa_level3'


class AccCoaLevel3Log(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    level2_id = models.IntegerField(blank=True, null=True)
    account_id = models.CharField(max_length=6, blank=True, null=True)
    account_name = models.CharField(max_length=120, blank=True, null=True)
    is_locked = models.BooleanField(blank=True, null=True)
    status = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'acc_coa_level3_log'


class AccCoaLevel4(models.Model):
    level3 = models.ForeignKey(AccCoaLevel3, models.DO_NOTHING)
    account_id = models.CharField(unique=True, max_length=12)
    account_name = models.CharField(max_length=150)
    description = models.CharField(max_length=250, blank=True, null=True)
    is_cash = models.BooleanField()
    is_bank = models.BooleanField()
    is_receivable = models.BooleanField()
    is_payable = models.BooleanField()
    status = models.CharField(max_length=10)
    created_at = models.DateTimeField()
    allow_cpv = models.BooleanField()
    allow_crv = models.BooleanField()
    allow_bpv = models.BooleanField()
    allow_brv = models.BooleanField()
    allow_jv = models.BooleanField()
    is_payable_deposit = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'acc_coa_level4'


class AccCoaLevel4Log(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    level3_id = models.IntegerField(blank=True, null=True)
    account_id = models.CharField(max_length=12, blank=True, null=True)
    account_name = models.CharField(max_length=150, blank=True, null=True)
    description = models.CharField(max_length=250, blank=True, null=True)
    is_cash = models.BooleanField(blank=True, null=True)
    is_bank = models.BooleanField(blank=True, null=True)
    is_receivable = models.BooleanField(blank=True, null=True)
    is_payable = models.BooleanField(blank=True, null=True)
    status = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    allow_cpv = models.BooleanField(blank=True, null=True)
    allow_crv = models.BooleanField(blank=True, null=True)
    allow_bpv = models.BooleanField(blank=True, null=True)
    allow_brv = models.BooleanField(blank=True, null=True)
    allow_jv = models.BooleanField(blank=True, null=True)
    is_payable_deposit = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'acc_coa_level4_log'


class AccFinancialYear(models.Model):
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'acc_financial_year'


class AccFinancialYearLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    is_closed = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'acc_financial_year_log'


class AccGeneralLedger(models.Model):
    voucher = models.ForeignKey('AccVoucherMaster', models.DO_NOTHING)
    account = models.ForeignKey(AccCoaLevel4, models.DO_NOTHING, to_field='account_id')
    date = models.DateField()
    debit = models.DecimalField(max_digits=15, decimal_places=2)
    credit = models.DecimalField(max_digits=15, decimal_places=2)
    narration = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'acc_general_ledger'


class AccGeneralLedgerLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    voucher_id = models.CharField(max_length=20, blank=True, null=True)
    account_id = models.CharField(max_length=12, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    debit = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    credit = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    narration = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'acc_general_ledger_log'


class AccSchoolPostingConfig(models.Model):
    config_key = models.CharField(unique=True, max_length=100)
    config_name = models.CharField(max_length=150)
    account = models.ForeignKey(AccCoaLevel4, models.DO_NOTHING, to_field='account_id', blank=True, null=True)
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'acc_school_posting_config'


class AccSchoolPostingConfigLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    config_key = models.CharField(max_length=100, blank=True, null=True)
    config_name = models.CharField(max_length=150, blank=True, null=True)
    account_id = models.CharField(max_length=12, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'acc_school_posting_config_log'


class AccVoucherDetail(models.Model):
    voucher = models.ForeignKey('AccVoucherMaster', models.DO_NOTHING)
    account = models.ForeignKey(AccCoaLevel4, models.DO_NOTHING, to_field='account_id')
    debit = models.DecimalField(max_digits=15, decimal_places=2)
    credit = models.DecimalField(max_digits=15, decimal_places=2)
    narration = models.CharField(max_length=255, blank=True, null=True)
    sub_ledger_type = models.CharField(max_length=50, blank=True, null=True)
    sub_ledger_id = models.IntegerField(blank=True, null=True)
    cost_center = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'acc_voucher_detail'


class AccVoucherDetailLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    voucher_id = models.CharField(max_length=20, blank=True, null=True)
    account_id = models.CharField(max_length=12, blank=True, null=True)
    debit = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    credit = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    narration = models.CharField(max_length=255, blank=True, null=True)
    sub_ledger_type = models.CharField(max_length=50, blank=True, null=True)
    sub_ledger_id = models.IntegerField(blank=True, null=True)
    cost_center = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'acc_voucher_detail_log'


class AccVoucherMaster(models.Model):
    voucher_no = models.CharField(primary_key=True, max_length=20)
    voucher_type = models.CharField(max_length=5)
    date = models.DateField()
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'acc_voucher_master'


class AccVoucherMasterLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    voucher_no = models.CharField(max_length=20, blank=True, null=True)
    voucher_type = models.CharField(max_length=5, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'acc_voucher_master_log'


class AccVoucherSequence(models.Model):
    voucher_type = models.CharField(max_length=10)
    fiscal_year = models.CharField(max_length=10)
    last_sequence = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'acc_voucher_sequence'
        unique_together = (('voucher_type', 'fiscal_year'),)


class AccVoucherSequenceLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    voucher_type = models.CharField(max_length=10, blank=True, null=True)
    fiscal_year = models.CharField(max_length=10, blank=True, null=True)
    last_sequence = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'acc_voucher_sequence_log'


class AttendanceHoliday(models.Model):
    id = models.BigAutoField(primary_key=True)
    session = models.CharField(max_length=20)
    date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    title = models.CharField(max_length=120)
    holiday_type = models.CharField(max_length=20)
    applies_to_all = models.BooleanField()
    class_field = models.CharField(max_length=50)
    section = models.CharField(max_length=10)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'attendance_holiday'


class AttendanceHolidayLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.BigIntegerField(blank=True, null=True)
    session = models.CharField(max_length=20, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    title = models.CharField(max_length=120, blank=True, null=True)
    holiday_type = models.CharField(max_length=20, blank=True, null=True)
    applies_to_all = models.BooleanField(blank=True, null=True)
    class_field = models.CharField(max_length=50, blank=True, null=True)
    section = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'attendance_holiday_log'


class AttendanceLock(models.Model):
    id = models.BigAutoField(primary_key=True)
    session = models.CharField(max_length=20)
    class_field = models.CharField(max_length=50)
    section = models.CharField(max_length=10)
    date = models.DateField()
    total_students = models.IntegerField()
    present_count = models.IntegerField()
    absent_count = models.IntegerField()
    leave_count = models.IntegerField()
    late_count = models.IntegerField()
    halfday_count = models.IntegerField()
    is_locked = models.BooleanField()
    marked_by = models.CharField(max_length=100)
    marked_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'attendance_lock'
        unique_together = (('session', 'class_field', 'section', 'date'),)


class AttendanceLockLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.BigIntegerField(blank=True, null=True)
    session = models.CharField(max_length=20, blank=True, null=True)
    class_field = models.CharField(max_length=50, blank=True, null=True)
    section = models.CharField(max_length=10, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    total_students = models.IntegerField(blank=True, null=True)
    present_count = models.IntegerField(blank=True, null=True)
    absent_count = models.IntegerField(blank=True, null=True)
    leave_count = models.IntegerField(blank=True, null=True)
    late_count = models.IntegerField(blank=True, null=True)
    halfday_count = models.IntegerField(blank=True, null=True)
    is_locked = models.BooleanField(blank=True, null=True)
    marked_by = models.CharField(max_length=100, blank=True, null=True)
    marked_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'attendance_lock_log'


class AttendanceSetting(models.Model):
    id = models.BigAutoField(primary_key=True)
    session = models.CharField(unique=True, max_length=20)
    working_days = models.CharField(max_length=100, blank=True, null=True)
    school_start_time = models.TimeField(blank=True, null=True)
    late_after = models.TimeField(blank=True, null=True)
    late_counts_present = models.BooleanField()
    leave_counts_present = models.BooleanField()
    min_percentage = models.IntegerField()
    allow_back_date = models.BooleanField()
    back_date_days = models.IntegerField()
    auto_lock_after = models.IntegerField()
    sms_on_absent = models.BooleanField()
    sms_template = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'attendance_setting'


class AttendanceSettingLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.BigIntegerField(blank=True, null=True)
    session = models.CharField(max_length=20, blank=True, null=True)
    working_days = models.CharField(max_length=100, blank=True, null=True)
    school_start_time = models.TimeField(blank=True, null=True)
    late_after = models.TimeField(blank=True, null=True)
    late_counts_present = models.BooleanField(blank=True, null=True)
    leave_counts_present = models.BooleanField(blank=True, null=True)
    min_percentage = models.IntegerField(blank=True, null=True)
    allow_back_date = models.BooleanField(blank=True, null=True)
    back_date_days = models.IntegerField(blank=True, null=True)
    auto_lock_after = models.IntegerField(blank=True, null=True)
    sms_on_absent = models.BooleanField(blank=True, null=True)
    sms_template = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'attendance_setting_log'


class AttendanceSummary(models.Model):
    id = models.BigAutoField(primary_key=True)
    session = models.CharField(max_length=20)
    student = models.ForeignKey('CoreStudent', models.DO_NOTHING)
    class_field = models.CharField(max_length=50)
    section = models.CharField(max_length=10)
    roll_no = models.CharField(max_length=30)
    year = models.IntegerField()
    month = models.SmallIntegerField()
    working_days = models.IntegerField()
    present_days = models.IntegerField()
    absent_days = models.IntegerField()
    leave_days = models.IntegerField()
    late_days = models.IntegerField()
    halfdays = models.IntegerField()
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'attendance_summary'
        unique_together = (('session', 'student', 'year', 'month'),)


class AttendanceSummaryLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.BigIntegerField(blank=True, null=True)
    session = models.CharField(max_length=20, blank=True, null=True)
    student_id = models.IntegerField(blank=True, null=True)
    class_field = models.CharField(max_length=50, blank=True, null=True)
    section = models.CharField(max_length=10, blank=True, null=True)
    roll_no = models.CharField(max_length=30, blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
    month = models.SmallIntegerField(blank=True, null=True)
    working_days = models.IntegerField(blank=True, null=True)
    present_days = models.IntegerField(blank=True, null=True)
    absent_days = models.IntegerField(blank=True, null=True)
    leave_days = models.IntegerField(blank=True, null=True)
    late_days = models.IntegerField(blank=True, null=True)
    halfdays = models.IntegerField(blank=True, null=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'attendance_summary_log'


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class CoreClassbasefee(models.Model):
    student_class = models.CharField(unique=True, max_length=50)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2)
    admission_fee = models.DecimalField(max_digits=10, decimal_places=2)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'core_classbasefee'


class CoreClassbasefeeLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    student_class = models.CharField(max_length=50, blank=True, null=True)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    admission_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'core_classbasefee_log'


class CoreClassspecialfee(models.Model):
    title = models.CharField(max_length=150)
    student_class = models.CharField(max_length=50)
    fee_month = models.IntegerField()
    fee_year = models.IntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'core_classspecialfee'


class CoreClassspecialfeeLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    title = models.CharField(max_length=150, blank=True, null=True)
    student_class = models.CharField(max_length=50, blank=True, null=True)
    fee_month = models.IntegerField(blank=True, null=True)
    fee_year = models.IntegerField(blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'core_classspecialfee_log'


class CoreStaff(models.Model):
    name = models.CharField(max_length=150)
    emp_id = models.CharField(unique=True, max_length=50)
    cnic = models.CharField(max_length=25, blank=True, null=True)
    role = models.CharField(max_length=100)
    qualification = models.CharField(max_length=150, blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    joining_date = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    contact = models.CharField(max_length=20, blank=True, null=True)
    emergency_contact = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=254, blank=True, null=True)
    photo = models.CharField(max_length=100, blank=True, null=True)
    cnic_photo = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField()
    is_active = models.BooleanField()
    address = models.TextField(blank=True, null=True)
    permanent_address = models.TextField(blank=True, null=True)
    password = models.CharField(max_length=128, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    marital_status = models.CharField(max_length=50, blank=True, null=True)
    relation_type = models.CharField(max_length=20, blank=True, null=True)
    relation_name = models.CharField(max_length=255, blank=True, null=True)
    ref_name = models.CharField(max_length=255, blank=True, null=True)
    ref_contact = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'core_staff'


class CoreStaffLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=150, blank=True, null=True)
    emp_id = models.CharField(max_length=50, blank=True, null=True)
    cnic = models.CharField(max_length=25, blank=True, null=True)
    role = models.CharField(max_length=100, blank=True, null=True)
    qualification = models.CharField(max_length=150, blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    joining_date = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    contact = models.CharField(max_length=20, blank=True, null=True)
    emergency_contact = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=254, blank=True, null=True)
    photo = models.CharField(max_length=100, blank=True, null=True)
    cnic_photo = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    permanent_address = models.TextField(blank=True, null=True)
    password = models.CharField(max_length=128, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    marital_status = models.CharField(max_length=50, blank=True, null=True)
    relation_type = models.CharField(max_length=20, blank=True, null=True)
    relation_name = models.CharField(max_length=255, blank=True, null=True)
    ref_name = models.CharField(max_length=255, blank=True, null=True)
    ref_contact = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'core_staff_log'


class CoreStaffRole(models.Model):
    role_name = models.CharField(unique=True, max_length=100)
    prefix = models.CharField(max_length=10)

    class Meta:
        managed = False
        db_table = 'core_staff_role'


class CoreStaffRoleLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    role_name = models.CharField(max_length=100, blank=True, null=True)
    prefix = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'core_staff_role_log'


class CoreStaffpayroll(models.Model):
    payroll_month = models.IntegerField()
    payroll_year = models.IntegerField()
    employee_type = models.CharField(max_length=20)
    teacher = models.ForeignKey('CoreTeacher', models.DO_NOTHING, blank=True, null=True)
    staff = models.ForeignKey(CoreStaff, models.DO_NOTHING, blank=True, null=True)
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    extra_allowance = models.DecimalField(max_digits=10, decimal_places=2)
    deduction = models.DecimalField(max_digits=10, decimal_places=2)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20)
    payment_date = models.DateField(blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    remarks = models.CharField(max_length=300, blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'core_staffpayroll'


class CoreStaffpayrollLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    payroll_month = models.IntegerField(blank=True, null=True)
    payroll_year = models.IntegerField(blank=True, null=True)
    employee_type = models.CharField(max_length=20, blank=True, null=True)
    teacher_id = models.IntegerField(blank=True, null=True)
    staff_id = models.IntegerField(blank=True, null=True)
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    extra_allowance = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    deduction = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    payment_date = models.DateField(blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    remarks = models.CharField(max_length=300, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'core_staffpayroll_log'


class CoreStudent(models.Model):
    name = models.CharField(max_length=150)
    father_name = models.CharField(max_length=150)
    father_cnic = models.CharField(max_length=20, blank=True, null=True)
    student_class = models.CharField(max_length=20)
    roll_no = models.CharField(max_length=50)
    dob = models.DateField(blank=True, null=True)
    enrolment_date = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    contact = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    admission_fee = models.DecimalField(max_digits=10, decimal_places=2)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2)
    transport_charges = models.DecimalField(max_digits=10, decimal_places=2)
    other_charges = models.DecimalField(max_digits=10, decimal_places=2)
    photo = models.CharField(max_length=100, blank=True, null=True)
    form_b_image = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField()
    is_active = models.BooleanField()
    previous_school = models.CharField(max_length=150, blank=True, null=True)
    permanent_address = models.TextField(blank=True, null=True)
    fee_concession = models.DecimalField(max_digits=10, decimal_places=2)
    password = models.CharField(max_length=128, blank=True, null=True)
    reg_no = models.CharField(max_length=50, blank=True, null=True)
    section = models.CharField(max_length=50, blank=True, null=True)
    mother_name = models.CharField(max_length=255, blank=True, null=True)
    challan_expiry_days = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'core_student'


class CoreStudentLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=150, blank=True, null=True)
    father_name = models.CharField(max_length=150, blank=True, null=True)
    father_cnic = models.CharField(max_length=20, blank=True, null=True)
    student_class = models.CharField(max_length=20, blank=True, null=True)
    roll_no = models.CharField(max_length=50, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    enrolment_date = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    contact = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    admission_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    transport_charges = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    other_charges = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    photo = models.CharField(max_length=100, blank=True, null=True)
    form_b_image = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)
    previous_school = models.CharField(max_length=150, blank=True, null=True)
    permanent_address = models.TextField(blank=True, null=True)
    fee_concession = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    password = models.CharField(max_length=128, blank=True, null=True)
    reg_no = models.CharField(max_length=50, blank=True, null=True)
    section = models.CharField(max_length=50, blank=True, null=True)
    mother_name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'core_student_log'


class CoreStudentfee(models.Model):
    challan_no = models.CharField(unique=True, max_length=50)
    student = models.ForeignKey(CoreStudent, models.DO_NOTHING)
    fee_month = models.IntegerField()
    fee_year = models.IntegerField()
    tuition_fee = models.DecimalField(max_digits=10, decimal_places=2)
    transport_fee = models.DecimalField(max_digits=10, decimal_places=2)
    admission_fee = models.DecimalField(max_digits=10, decimal_places=2)
    other_charges = models.DecimalField(max_digits=10, decimal_places=2)
    fine = models.DecimalField(max_digits=10, decimal_places=2)
    arrears = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20)
    payment_date = models.DateField(blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    due_date = models.DateField()
    issued_date = models.DateField()
    notes = models.CharField(max_length=250, blank=True, null=True)
    created_at = models.DateTimeField()
    advance_fee = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'core_studentfee'


class CoreStudentfeeLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    challan_no = models.CharField(max_length=50, blank=True, null=True)
    student_id = models.IntegerField(blank=True, null=True)
    fee_month = models.IntegerField(blank=True, null=True)
    fee_year = models.IntegerField(blank=True, null=True)
    tuition_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    transport_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    admission_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    other_charges = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    fine = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    arrears = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    payment_date = models.DateField(blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    issued_date = models.DateField(blank=True, null=True)
    notes = models.CharField(max_length=250, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    advance_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'core_studentfee_log'


class CoreTeacher(models.Model):
    name = models.CharField(max_length=150)
    emp_id = models.CharField(unique=True, max_length=50)
    cnic = models.CharField(max_length=25, blank=True, null=True)
    subject = models.CharField(max_length=100)
    qualification = models.CharField(max_length=150, blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    joining_date = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    contact = models.CharField(max_length=20, blank=True, null=True)
    emergency_contact = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=254, blank=True, null=True)
    photo = models.CharField(max_length=100, blank=True, null=True)
    cnic_photo = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField()
    is_active = models.BooleanField()
    address = models.TextField(blank=True, null=True)
    permanent_address = models.TextField(blank=True, null=True)
    password = models.CharField(max_length=128, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    marital_status = models.CharField(max_length=50, blank=True, null=True)
    relation_type = models.CharField(max_length=20, blank=True, null=True)
    relation_name = models.CharField(max_length=255, blank=True, null=True)
    ref_name = models.CharField(max_length=255, blank=True, null=True)
    ref_contact = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'core_teacher'


class CoreTeacherLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=150, blank=True, null=True)
    emp_id = models.CharField(max_length=50, blank=True, null=True)
    cnic = models.CharField(max_length=25, blank=True, null=True)
    subject = models.CharField(max_length=100, blank=True, null=True)
    qualification = models.CharField(max_length=150, blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    joining_date = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    contact = models.CharField(max_length=20, blank=True, null=True)
    emergency_contact = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=254, blank=True, null=True)
    photo = models.CharField(max_length=100, blank=True, null=True)
    cnic_photo = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    permanent_address = models.TextField(blank=True, null=True)
    password = models.CharField(max_length=128, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    marital_status = models.CharField(max_length=50, blank=True, null=True)
    relation_type = models.CharField(max_length=20, blank=True, null=True)
    relation_name = models.CharField(max_length=255, blank=True, null=True)
    ref_name = models.CharField(max_length=255, blank=True, null=True)
    ref_contact = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'core_teacher_log'


class CoreUserModulePermissions(models.Model):
    mode = models.CharField(max_length=10)
    target = models.CharField(max_length=100)
    section = models.CharField(max_length=50)
    module_name = models.CharField(max_length=50)
    can_view = models.BooleanField()
    can_add = models.BooleanField()
    can_edit = models.BooleanField()
    can_delete = models.BooleanField()
    can_print = models.BooleanField()
    updated_by = models.CharField(max_length=150, blank=True, null=True)
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'core_user_module_permissions'
        unique_together = (('mode', 'target', 'section', 'module_name'),)


class CoreUserModulePermissionsLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    mode = models.CharField(max_length=10, blank=True, null=True)
    target = models.CharField(max_length=100, blank=True, null=True)
    section = models.CharField(max_length=50, blank=True, null=True)
    module_name = models.CharField(max_length=50, blank=True, null=True)
    can_view = models.BooleanField(blank=True, null=True)
    can_add = models.BooleanField(blank=True, null=True)
    can_edit = models.BooleanField(blank=True, null=True)
    can_delete = models.BooleanField(blank=True, null=True)
    can_print = models.BooleanField(blank=True, null=True)
    updated_by = models.CharField(max_length=150, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'core_user_module_permissions_log'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.SmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class Exam(models.Model):
    student_class = models.CharField(max_length=20)
    subject = models.CharField(max_length=100)
    total_marks = models.IntegerField(blank=True, null=True)
    teacher = models.ForeignKey(CoreTeacher, models.DO_NOTHING, blank=True, null=True)
    exam_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    term = models.CharField(max_length=10)
    start_time = models.TimeField()
    end_time = models.TimeField()
    passing_marks = models.FloatField(blank=True, null=True)
    section = models.CharField(max_length=10)

    class Meta:
        managed = False
        db_table = 'exam'
        unique_together = (('teacher', 'subject', 'exam_date', 'start_time', 'end_time'), ('student_class', 'term', 'subject', 'exam_date', 'start_time', 'end_time'),)


class ExamLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    student_class = models.CharField(max_length=20, blank=True, null=True)
    subject = models.CharField(max_length=100, blank=True, null=True)
    total_marks = models.IntegerField(blank=True, null=True)
    teacher_id = models.IntegerField(blank=True, null=True)
    exam_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    term = models.CharField(max_length=10, blank=True, null=True)
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    passing_marks = models.FloatField(blank=True, null=True)
    section = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'exam_log'


class ExamMark(models.Model):
    exam = models.ForeignKey(Exam, models.DO_NOTHING)
    student = models.ForeignKey(CoreStudent, models.DO_NOTHING)
    obtained_marks = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'exam_mark'


class ExamMarkLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    exam_id = models.IntegerField(blank=True, null=True)
    student_id = models.IntegerField(blank=True, null=True)
    obtained_marks = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'exam_mark_log'


class FeeChallan(models.Model):
    challan_no = models.CharField(unique=True, max_length=50)
    student = models.ForeignKey(CoreStudent, models.DO_NOTHING)
    fee_month = models.IntegerField()
    fee_year = models.IntegerField()
    tuition_fee = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    transport_fee = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    admission_fee = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    other_charges = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    fine = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    previous_arrears = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=18, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    balance = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=20, blank=True, null=True)
    issue_date = models.DateField()
    due_date = models.DateField()
    payment_date = models.DateField(blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    advance_fee = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    session_name = models.CharField(max_length=20, blank=True, null=True)
    class_field = models.CharField(max_length=50, blank=True, null=True)
    section = models.CharField(max_length=10, blank=True, null=True)
    roll_no = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'fee_challan'


class FeeChallanEditLog(models.Model):
    challan_id = models.IntegerField()
    student_id = models.IntegerField()
    edited_at = models.DateTimeField()
    edited_by = models.CharField(max_length=150, blank=True, null=True)
    reason = models.TextField()
    old_data = models.TextField(blank=True, null=True)
    new_data = models.TextField(blank=True, null=True)
    affected = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'fee_challan_edit_log'


class FeeChallanLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    challan_no = models.CharField(max_length=50, blank=True, null=True)
    student_id = models.IntegerField(blank=True, null=True)
    fee_month = models.IntegerField(blank=True, null=True)
    fee_year = models.IntegerField(blank=True, null=True)
    tuition_fee = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    transport_fee = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    admission_fee = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    other_charges = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    fine = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    previous_arrears = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    paid_amount = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    balance = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    issue_date = models.DateField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    payment_date = models.DateField(blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    advance_fee = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'fee_challan_log'


class NCategory(models.Model):
    category_name = models.CharField(unique=True, max_length=100)

    class Meta:
        managed = False
        db_table = 'n_category'


class NCategoryLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    category_name = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'n_category_log'


class NoticeBoard(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(unique=True, max_length=20)
    title = models.CharField(max_length=200)
    body = models.TextField()
    category = models.CharField(max_length=20)
    priority = models.CharField(max_length=10)
    status = models.CharField(max_length=15)
    audience = models.TextField()
    publish_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    attachment = models.CharField(max_length=500, blank=True, null=True)
    pinned = models.BooleanField()
    views = models.IntegerField()
    author = models.ForeignKey(AuthUser, models.DO_NOTHING, blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'notice_board'


class NoticeBoardLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.BigIntegerField(blank=True, null=True)
    code = models.CharField(max_length=20, blank=True, null=True)
    title = models.CharField(max_length=200, blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=20, blank=True, null=True)
    priority = models.CharField(max_length=10, blank=True, null=True)
    status = models.CharField(max_length=15, blank=True, null=True)
    audience = models.TextField(blank=True, null=True)
    publish_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    attachment = models.CharField(max_length=500, blank=True, null=True)
    pinned = models.BooleanField(blank=True, null=True)
    views = models.IntegerField(blank=True, null=True)
    author_id = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'notice_board_log'


class PromotionDraft(models.Model):
    student = models.ForeignKey(CoreStudent, models.DO_NOTHING)
    target_session = models.CharField(max_length=50)
    from_class = models.CharField(max_length=50)
    from_section = models.CharField(max_length=50)
    old_roll_no = models.CharField(max_length=50)
    to_class = models.CharField(max_length=50)
    to_section = models.CharField(max_length=50)
    new_roll_no = models.CharField(max_length=50)
    is_promoted = models.BooleanField()
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'promotion_draft'


class PromotionDraftLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    student_id = models.IntegerField(blank=True, null=True)
    target_session = models.CharField(max_length=50, blank=True, null=True)
    from_class = models.CharField(max_length=50, blank=True, null=True)
    from_section = models.CharField(max_length=50, blank=True, null=True)
    old_roll_no = models.CharField(max_length=50, blank=True, null=True)
    to_class = models.CharField(max_length=50, blank=True, null=True)
    to_section = models.CharField(max_length=50, blank=True, null=True)
    new_roll_no = models.CharField(max_length=50, blank=True, null=True)
    is_promoted = models.BooleanField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'promotion_draft_log'


class StaffAttendance(models.Model):
    id = models.BigAutoField(primary_key=True)
    session = models.CharField(max_length=20)
    emp_id = models.CharField(max_length=30)
    staff_name = models.CharField(max_length=150)
    designation = models.CharField(max_length=80)
    staff_type = models.CharField(max_length=20)
    date = models.DateField()
    status = models.CharField(max_length=1)
    check_in = models.TimeField(blank=True, null=True)
    check_out = models.TimeField(blank=True, null=True)
    remarks = models.CharField(max_length=200)
    leave_type = models.CharField(max_length=20)
    marked_by = models.CharField(max_length=100)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'staff_attendance'
        unique_together = (('session', 'emp_id', 'date'),)


class StaffAttendanceLock(models.Model):
    id = models.BigAutoField(primary_key=True)
    session = models.CharField(max_length=20)
    date = models.DateField()
    staff_type = models.CharField(max_length=20)
    total_staff = models.IntegerField()
    present_count = models.IntegerField()
    absent_count = models.IntegerField()
    leave_count = models.IntegerField()
    late_count = models.IntegerField()
    halfday_count = models.IntegerField()
    is_locked = models.BooleanField()
    marked_by = models.CharField(max_length=100)
    marked_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'staff_attendance_lock'
        unique_together = (('session', 'date', 'staff_type'),)


class StaffAttendanceLockLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.BigIntegerField(blank=True, null=True)
    session = models.CharField(max_length=20, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    staff_type = models.CharField(max_length=20, blank=True, null=True)
    total_staff = models.IntegerField(blank=True, null=True)
    present_count = models.IntegerField(blank=True, null=True)
    absent_count = models.IntegerField(blank=True, null=True)
    leave_count = models.IntegerField(blank=True, null=True)
    late_count = models.IntegerField(blank=True, null=True)
    halfday_count = models.IntegerField(blank=True, null=True)
    is_locked = models.BooleanField(blank=True, null=True)
    marked_by = models.CharField(max_length=100, blank=True, null=True)
    marked_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'staff_attendance_lock_log'


class StaffAttendanceLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.BigIntegerField(blank=True, null=True)
    session = models.CharField(max_length=20, blank=True, null=True)
    emp_id = models.CharField(max_length=30, blank=True, null=True)
    staff_name = models.CharField(max_length=150, blank=True, null=True)
    designation = models.CharField(max_length=80, blank=True, null=True)
    staff_type = models.CharField(max_length=20, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=1, blank=True, null=True)
    check_in = models.TimeField(blank=True, null=True)
    check_out = models.TimeField(blank=True, null=True)
    remarks = models.CharField(max_length=200, blank=True, null=True)
    leave_type = models.CharField(max_length=20, blank=True, null=True)
    marked_by = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'staff_attendance_log'


class StudentAlumni(models.Model):
    student = models.ForeignKey(CoreStudent, models.DO_NOTHING)
    reg_no = models.CharField(max_length=50)
    student_name = models.CharField(max_length=255)
    father_name = models.CharField(max_length=255)
    passed_class = models.CharField(max_length=50)
    passed_section = models.CharField(max_length=50)
    passed_session = models.CharField(max_length=50)
    passing_date = models.DateField(blank=True, null=True)
    remaining_dues = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    remarks = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'student_alumni'


class StudentAlumniLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    student_id = models.IntegerField(blank=True, null=True)
    reg_no = models.CharField(max_length=50, blank=True, null=True)
    student_name = models.CharField(max_length=255, blank=True, null=True)
    father_name = models.CharField(max_length=255, blank=True, null=True)
    passed_class = models.CharField(max_length=50, blank=True, null=True)
    passed_section = models.CharField(max_length=50, blank=True, null=True)
    passed_session = models.CharField(max_length=50, blank=True, null=True)
    passing_date = models.DateField(blank=True, null=True)
    remaining_dues = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    remarks = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'student_alumni_log'


class StudentAttendance(models.Model):
    id = models.BigAutoField(primary_key=True)
    session = models.CharField(max_length=20)
    student = models.ForeignKey(CoreStudent, models.DO_NOTHING)
    class_field = models.CharField(max_length=50)
    section = models.CharField(max_length=10)
    roll_no = models.CharField(max_length=30)
    student_name = models.CharField(max_length=150)
    date = models.DateField()
    status = models.CharField(max_length=1)
    remarks = models.CharField(max_length=200)
    is_notified = models.BooleanField()
    marked_by = models.CharField(max_length=100)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'student_attendance'
        unique_together = (('session', 'student', 'date'),)


class StudentAttendanceLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.BigIntegerField(blank=True, null=True)
    session = models.CharField(max_length=20, blank=True, null=True)
    student_id = models.IntegerField(blank=True, null=True)
    class_field = models.CharField(max_length=50, blank=True, null=True)
    section = models.CharField(max_length=10, blank=True, null=True)
    roll_no = models.CharField(max_length=30, blank=True, null=True)
    student_name = models.CharField(max_length=150, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=1, blank=True, null=True)
    remarks = models.CharField(max_length=200, blank=True, null=True)
    is_notified = models.BooleanField(blank=True, null=True)
    marked_by = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'student_attendance_log'


class StudentResultRemark(models.Model):
    student = models.ForeignKey(CoreStudent, models.DO_NOTHING)
    student_class = models.CharField(max_length=20)
    term = models.CharField(max_length=10)
    remarks = models.CharField(max_length=500, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'student_result_remark'
        unique_together = (('student', 'student_class', 'term'),)


class StudentResultRemarkLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.IntegerField(blank=True, null=True)
    student_id = models.IntegerField(blank=True, null=True)
    student_class = models.CharField(max_length=20, blank=True, null=True)
    term = models.CharField(max_length=10, blank=True, null=True)
    remarks = models.CharField(max_length=500, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'student_result_remark_log'


class Sysdiagrams(models.Model):
    name = models.CharField(max_length=128)
    principal_id = models.IntegerField()
    diagram_id = models.AutoField(primary_key=True)
    version = models.IntegerField(blank=True, null=True)
    definition = models.BinaryField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sysdiagrams'
        unique_together = (('principal_id', 'name'),)


class TransportRoute(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(unique=True, max_length=20)
    name = models.CharField(max_length=120)
    distance = models.CharField(max_length=40)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2)
    pickup_start = models.TimeField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'transport_route'


class TransportRouteLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.BigIntegerField(blank=True, null=True)
    code = models.CharField(max_length=20, blank=True, null=True)
    name = models.CharField(max_length=120, blank=True, null=True)
    distance = models.CharField(max_length=40, blank=True, null=True)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    pickup_start = models.TimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'transport_route_log'


class TransportRouteVehicles(models.Model):
    id = models.BigAutoField(primary_key=True)
    route = models.ForeignKey(TransportRoute, models.DO_NOTHING)
    vehicle = models.ForeignKey('TransportVehicle', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'transport_route_vehicles'
        unique_together = (('route', 'vehicle'),)


class TransportStop(models.Model):
    id = models.BigAutoField(primary_key=True)
    route = models.ForeignKey(TransportRoute, models.DO_NOTHING)
    name = models.CharField(max_length=150)
    time = models.TimeField(blank=True, null=True)
    order = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'transport_stop'


class TransportStopLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.BigIntegerField(blank=True, null=True)
    route_id = models.BigIntegerField(blank=True, null=True)
    name = models.CharField(max_length=150, blank=True, null=True)
    time = models.TimeField(blank=True, null=True)
    order = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'transport_stop_log'


class TransportStudentAssignment(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(unique=True, max_length=20)
    student_id = models.BigIntegerField()
    route = models.ForeignKey(TransportRoute, models.DO_NOTHING)
    vehicle = models.ForeignKey('TransportVehicle', models.DO_NOTHING)
    stop = models.ForeignKey(TransportStop, models.DO_NOTHING, blank=True, null=True)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2)
    pickup_point = models.CharField(max_length=200)
    guardian_contact = models.CharField(max_length=20)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField()
    notes = models.TextField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'transport_student_assignment'


class TransportStudentAssignmentLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.BigIntegerField(blank=True, null=True)
    code = models.CharField(max_length=20, blank=True, null=True)
    student_id = models.BigIntegerField(blank=True, null=True)
    route_id = models.BigIntegerField(blank=True, null=True)
    vehicle_id = models.BigIntegerField(blank=True, null=True)
    stop_id = models.BigIntegerField(blank=True, null=True)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    pickup_point = models.CharField(max_length=200, blank=True, null=True)
    guardian_contact = models.CharField(max_length=20, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'transport_student_assignment_log'


class TransportVehicle(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(unique=True, max_length=20)
    name = models.CharField(max_length=80)
    vtype = models.CharField(max_length=20)
    reg_no = models.CharField(unique=True, max_length=30)
    model_year = models.CharField(max_length=40)
    capacity = models.IntegerField()
    driver_id = models.BigIntegerField(blank=True, null=True)
    status = models.CharField(max_length=20)
    notes = models.TextField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'transport_vehicle'


class TransportVehicleLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    log_action = models.CharField(max_length=10)
    log_changed_by = models.IntegerField(blank=True, null=True)
    log_changed_by_name = models.CharField(max_length=120, blank=True, null=True)
    log_changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    log_ip = models.CharField(max_length=45, blank=True, null=True)
    log_source = models.CharField(max_length=20)
    log_at = models.DateTimeField()
    id = models.BigIntegerField(blank=True, null=True)
    code = models.CharField(max_length=20, blank=True, null=True)
    name = models.CharField(max_length=80, blank=True, null=True)
    vtype = models.CharField(max_length=20, blank=True, null=True)
    reg_no = models.CharField(max_length=30, blank=True, null=True)
    model_year = models.CharField(max_length=40, blank=True, null=True)
    capacity = models.IntegerField(blank=True, null=True)
    driver_id = models.BigIntegerField(blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'transport_vehicle_log'

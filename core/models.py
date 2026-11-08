from django.db import models
from django.conf import settings
from django.utils import timezone

class ClassDefination(models.Model):
    class_field = models.CharField(db_column='class', max_length=50)
    section = models.CharField(max_length=50)
    room_number = models.CharField(max_length=50)
    max_capacity = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    created_at = models.DateField()

    class Meta:
        managed = False
        db_table = 'Class_defination'
    
class SubjectDefination(models.Model):
    subject_name = models.CharField(max_length=100)
    subject_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    created_date = models.DateField()

    class Meta:
        managed = False
        db_table = 'Subject_Defination'
        

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
    permanent_address = models.TextField(blank=True, null=True)
    previous_school = models.CharField(max_length=150, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    admission_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    transport_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    other_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    photo = models.ImageField(upload_to='students/photos/', blank=True, null=True)
    form_b_image = models.ImageField(upload_to='students/form_b/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    password = models.CharField(max_length=128, blank=True, null=True)
    reg_no = models.CharField(max_length=50, blank=True, null=True)
    section = models.CharField(max_length=50, blank=True, null=True)
    mother_name = models.CharField(max_length=255, blank=True, null=True)
    challan_expiry_days = models.IntegerField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'core_student'

    def __str__(self):
        return f"{self.name} - {self.student_class} ({self.roll_no})"


class CoreTeacher(models.Model):
    name = models.CharField(max_length=150)
    emp_id = models.CharField(unique=True, max_length=50)
    cnic = models.CharField(max_length=25, blank=True, null=True)
    subject = models.CharField(max_length=100)
    qualification = models.CharField(max_length=150, blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    joining_date = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    contact = models.CharField(max_length=20, blank=True, null=True)
    emergency_contact = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=254, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    permanent_address = models.TextField(blank=True, null=True)
    photo = models.ImageField(upload_to='teachers/photos/', blank=True, null=True)
    cnic_photo = models.ImageField(upload_to='teachers/cnic/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    password = models.CharField(max_length=128, blank=True, null=True)
    # Yeh fields CoreTeacher aur CoreStaff dono models mein shamil karein:
    dob = models.DateField(blank=True, null=True)
    marital_status = models.CharField(max_length=50, blank=True, null=True)
    relation_type = models.CharField(max_length=20, blank=True, null=True)  # S/O, D/O, W/O
    relation_name = models.CharField(max_length=255, blank=True, null=True)
    ref_name = models.CharField(max_length=255, blank=True, null=True)
    ref_contact = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'core_teacher'

    def __str__(self):
        return f"{self.name} ({self.emp_id})"


class CoreStaff(models.Model):
    name = models.CharField(max_length=150)
    emp_id = models.CharField(unique=True, max_length=50)
    cnic = models.CharField(max_length=25, blank=True, null=True)
    role = models.CharField(max_length=100)
    qualification = models.CharField(max_length=150, blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    joining_date = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    contact = models.CharField(max_length=20, blank=True, null=True)
    emergency_contact = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=254, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    permanent_address = models.TextField(blank=True, null=True)
    photo = models.ImageField(upload_to='staff/photos/', blank=True, null=True)
    cnic_photo = models.ImageField(upload_to='staff/cnic/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
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

    def __str__(self):
        return f"{self.name} - {self.role} ({self.emp_id})"

class CoreStaffRole(models.Model):
    role_name = models.CharField(max_length=100, unique=True)
    prefix = models.CharField(max_length=10)

    class Meta:
        db_table = 'core_staff_role'
        managed = False

    def __str__(self):
        return f"{self.role_name} ({self.prefix})"

class CoreStudentFee(models.Model):
    challan_no = models.CharField(max_length=50, unique=True)
    student = models.ForeignKey('CoreStudent', on_delete=models.CASCADE, db_column='student_id')
    fee_month = models.IntegerField()
    fee_year = models.IntegerField()
    tuition_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    transport_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    admission_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    other_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    fine = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    arrears = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    advance_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, default='Unpaid')
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    due_date = models.DateField()
    issued_date = models.DateField(auto_now_add=True)
    notes = models.CharField(max_length=250, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'core_studentfee'

    def __str__(self):
        return f"{self.challan_no} - {self.student.name} ({self.status})"


class CoreStaffPayroll(models.Model):
    payroll_month = models.IntegerField()
    payroll_year = models.IntegerField()
    employee_type = models.CharField(max_length=20)  # 'Teacher' or 'Staff'
    teacher = models.ForeignKey('CoreTeacher', on_delete=models.CASCADE, null=True, blank=True, db_column='teacher_id')
    staff = models.ForeignKey('CoreStaff', on_delete=models.CASCADE, null=True, blank=True, db_column='staff_id')
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    extra_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, default='Pending')
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    remarks = models.CharField(max_length=300, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'core_staffpayroll'

    def __str__(self):
        emp_name = self.teacher.name if self.teacher else (self.staff.name if self.staff else 'Unknown')
        return f"{emp_name} - {self.payroll_month}/{self.payroll_year} ({self.status})"  
    
class NCategory(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    category_name = models.CharField(unique=True, max_length=100, db_collation='SQL_Latin1_General_CP1_CI_AS')

    class Meta:
        managed = False
        db_table = 'n_category'
    def __str__(self):
        return self.category_name

class Notice(models.Model):

    PRIORITY_CHOICES = (
        ('Low', 'Low'),
        ('Normal', 'Normal'),
        ('High', 'High'),
    )

    STATUS_CHOICES = (
        ('Draft', 'Draft'),
        ('Scheduled', 'Scheduled'),
        ('Published', 'Published'),
        ('Expired', 'Expired'),
    )

    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    body = models.TextField()
    category = models.ForeignKey(
    NCategory,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='notices',
    db_column='category',
    to_field='category_name'
)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Normal')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Draft')
    audience = models.JSONField(default=list, blank=True)
    publish_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    attachment = models.FileField(upload_to='notices/%Y/%m/', blank=True, null=True)
    pinned = models.BooleanField(default=False)
    views = models.PositiveIntegerField(default=0)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notices'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notice_board'
        ordering = ['-pinned', '-created_at']

    def __str__(self):
        return f"{self.code} — {self.title}"
    
# TRANSPORT

class Vehicle(models.Model):
    TYPE_CHOICES = [('Bus', 'Bus'), ('Van', 'Van'), ('Coaster', 'Coaster')]
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Maintenance', 'Maintenance'),
        ('Inactive', 'Inactive'),
    ]

    code = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=80, blank=True)
    vtype = models.CharField(max_length=20, choices=TYPE_CHOICES)
    reg_no = models.CharField(max_length=30, unique=True)
    model_year = models.CharField(max_length=40, blank=True)
    capacity = models.PositiveIntegerField(default=0)
    driver = models.OneToOneField(
        'CoreStaff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vehicle',
        db_constraint=False,  
        # reverse: staff_member.vehicle → Vehicle or DoesNotExist
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transport_vehicle'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} — {self.reg_no}"

    @property
    def used_seats(self):
        """Number of students currently riding this vehicle."""
        return self.student_assignments.filter(is_active=True).count()

    @property
    def available_seats(self):
        return max(self.capacity - self.used_seats, 0)

    @property
    def is_full(self):
        return self.used_seats >= self.capacity

    @property
    def occupancy_percent(self):
        if not self.capacity:
            return 0
        return round((self.used_seats / self.capacity) * 100)


class Route(models.Model):
    code = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=120)
    distance = models.CharField(max_length=40, blank=True)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='routes')
    vehicles = models.ManyToManyField(
    Vehicle,
    blank=True,
    related_name='routes'
)
    pickup_start = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transport_route'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} — {self.name}"

    @property
    def student_count(self):
        return 0


class Stop(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stops')
    name = models.CharField(max_length=150)
    time = models.TimeField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'transport_stop'
        ordering = ['route', 'order']

    def __str__(self):
        return f"{self.route.code} · {self.name}"

# ═══════════════════════════════════════════════════
# STUDENT ↔ VEHICLE ASSIGNMENT
# ═══════════════════════════════════════════════════

class StudentTransport(models.Model):
    """One active assignment per student."""

    code = models.CharField(max_length=20, unique=True, editable=False)

    student = models.ForeignKey(
        'CoreStudent',
        on_delete=models.CASCADE,
        related_name='transport_assignments',
        db_constraint=False,          # CoreStudent is unmanaged
    )

    route = models.ForeignKey(
        'Route',
        on_delete=models.CASCADE,
        related_name='student_assignments',
    )

    vehicle = models.ForeignKey(
        'Vehicle',
        on_delete=models.CASCADE,
        related_name='student_assignments',
    )

    stop = models.ForeignKey(
        'Stop',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_assignments',
    )

    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pickup_point = models.CharField(max_length=200, blank=True)
    guardian_contact = models.CharField(max_length=20, blank=True)

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transport_student_assignment'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} — {self.student.name} → {self.vehicle.code}"
    
class CoreClassSpecialFee(models.Model):
    title = models.CharField(max_length=100)
    student_class = models.CharField(max_length=50)
    fee_month = models.IntegerField()
    fee_year = models.IntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'core_classspecialfee'

    def __str__(self):
        return f"{self.title} - Class {self.student_class} ({self.fee_month}/{self.fee_year}) - Rs. {self.amount}"  
 
class CoreExam(models.Model):
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
      
class CoreExamMark(models.Model):
    exam = models.ForeignKey('CoreExam', models.DO_NOTHING, db_column='exam_id')
    student = models.ForeignKey('CoreStudent', models.DO_NOTHING, db_column='student_id')
    obtained_marks = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'exam_mark'
        unique_together = (('exam', 'student'),)

    # ✅ CORRECT: Outdented to model level
    @property
    def remarks(self):
        if self.obtained_marks is None or self.exam.passing_marks is None:
            return "-"
        return "Pass" if float(self.obtained_marks) >= float(self.exam.passing_marks) else "Fail"

    @property
    def grade(self):
        if self.obtained_marks is None or self.exam.passing_marks is None:
            return "-"

        obtained = float(self.obtained_marks)
        passing = float(self.exam.passing_marks)
        total = float(self.exam.total_marks) if self.exam.total_marks else 100.0

        if obtained < passing:
            return "F"

        pct = (obtained / total) * 100 if total > 0 else 0

        if pct >= 80: return "A+"
        if pct >= 70: return "A"
        if pct >= 60: return "B"
        if pct >= 50: return "C"
    
        return "D"


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

class StudentResultRemark(models.Model):
    student = models.ForeignKey('CoreStudent', models.DO_NOTHING, db_column='student_id')
    student_class = models.CharField(max_length=20)
    term = models.CharField(max_length=10)
    remarks = models.CharField(max_length=500, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'student_result_remark'
        unique_together = (('student', 'student_class', 'term'),)      
        
class CoreClassBaseFee(models.Model):
    student_class = models.CharField(max_length=50, unique=True)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    admission_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'core_classbasefee'

    def __str__(self):
        return f"Class {self.student_class} - Rs. {self.monthly_fee}"
    
    
class SchoolProfile(models.Model):
    #id = models.AutoField()
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
        
class TimetableSlot(models.Model):
    session = models.CharField(max_length=20)
    class_field = models.CharField(db_column='class', max_length=50)
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
        
class TimetableDay(models.Model):
    day_of_week = models.SmallIntegerField(unique=True)
    name = models.CharField(max_length=10)
    is_working = models.BooleanField()
    last_period_no = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Timetable_Day'
        
class StudentAttendance(models.Model):
    id = models.BigAutoField(primary_key=True)
    session = models.CharField(max_length=20)
    student = models.ForeignKey('CoreStudent', models.DO_NOTHING)
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

class AcademicSession(models.Model):
    session_name = models.CharField(max_length=50, unique=True)
    is_current = models.BooleanField(default=False)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'academic_session'
        managed = False

    def __str__(self):
        return self.session_name


class PromotionDraft(models.Model):
    student = models.ForeignKey('CoreStudent', on_delete=models.CASCADE, db_column='student_id')
    target_session = models.CharField(max_length=50)
    from_class = models.CharField(max_length=50)
    from_section = models.CharField(max_length=50)
    old_roll_no = models.CharField(max_length=50)
    to_class = models.CharField(max_length=50)
    to_section = models.CharField(max_length=50)
    new_roll_no = models.CharField(max_length=50)
    is_promoted = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'promotion_draft'
        managed = False                                         
        
class StudentAlumni(models.Model):
    student = models.ForeignKey('CoreStudent', on_delete=models.CASCADE, db_column='student_id')
    reg_no = models.CharField(max_length=50)
    student_name = models.CharField(max_length=255)
    father_name = models.CharField(max_length=255)
    passed_class = models.CharField(max_length=50)
    passed_section = models.CharField(max_length=50)
    passed_session = models.CharField(max_length=50)
    passing_date = models.DateField(auto_now_add=True)
    remaining_dues = models.DecimalField(max_digits=18, decimal_places=2, default=0.00)
    remarks = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'student_alumni'
        managed = False

    def __str__(self):
        return f"{self.reg_no} - {self.student_name} ({self.passed_session})"        

class FeeChallan(models.Model):
    challan_no = models.CharField(max_length=50, unique=True)
    student = models.ForeignKey('CoreStudent', on_delete=models.CASCADE, db_column='student_id')

    # ✅ NEW SNAPSHOT FIELDS
    session_name = models.CharField(max_length=20, null=True, blank=True)
    class_field  = models.CharField(max_length=50, null=True, blank=True)
    section      = models.CharField(max_length=10, null=True, blank=True)
    roll_no      = models.CharField(max_length=30, null=True, blank=True)

    fee_month = models.IntegerField()
    fee_year = models.IntegerField()
    tuition_fee = models.DecimalField(max_digits=18, decimal_places=2, default=0.00)
    transport_fee = models.DecimalField(max_digits=18, decimal_places=2, default=0.00)
    admission_fee = models.DecimalField(max_digits=18, decimal_places=2, default=0.00)
    other_charges = models.DecimalField(max_digits=18, decimal_places=2, default=0.00)
    fine = models.DecimalField(max_digits=18, decimal_places=2, default=0.00)
    previous_arrears = models.DecimalField(max_digits=18, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=18, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0.00)
    advance_fee = models.DecimalField(max_digits=18, decimal_places=2, default=0.00)
    balance = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=20, default='Unpaid')
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'fee_challan'
        managed = False

class FeeChallanEditLog(models.Model):
    id = models.AutoField(primary_key=True)  # DB me column "id" hoga
    challan_id = models.IntegerField()       # fee_challan.id store karega
    student_id = models.IntegerField()

    edited_at = models.DateTimeField(default=timezone.now)  # ✅ FIX
    edited_by = models.CharField(max_length=150, blank=True, null=True)
    reason = models.TextField()

    old_data = models.TextField(blank=True, null=True)   # JSON string
    new_data = models.TextField(blank=True, null=True)   # JSON string
    affected = models.TextField(blank=True, null=True)   # JSON string

    class Meta:
        db_table = 'fee_challan_edit_log'
        managed = False

    def __str__(self):
        return f"EditLog challan_id={self.challan_id} student_id={self.student_id}"



class CoreUserModulePermission(models.Model):
    mode = models.CharField(max_length=10)
    target = models.CharField(max_length=100)
    section = models.CharField(max_length=50, default='', blank=True)
    module_name = models.CharField(max_length=50)

    can_view = models.BooleanField(default=False)
    can_add = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_print = models.BooleanField(default=False)

    updated_by = models.CharField(max_length=150, null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'core_user_module_permissions'
        unique_together = (('mode', 'target', 'section', 'module_name'),)



# ==============================
# ACCOUNTANT / GENERAL LEDGER
# ==============================


class AccCoaLevel1(models.Model):
    account_id = models.CharField(unique=True, max_length=2)
    account_name = models.CharField(max_length=100)
    nature = models.CharField(max_length=10)
    is_locked = models.BooleanField(default=False)
    status = models.CharField(max_length=10, default='Active')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = 'acc_coa_level1'
        ordering = ['account_id']

    def __str__(self):
        return f"{self.account_id} - {self.account_name}"


class AccCoaLevel2(models.Model):
    level1 = models.ForeignKey(AccCoaLevel1, models.DO_NOTHING)
    account_id = models.CharField(unique=True, max_length=4)
    account_name = models.CharField(max_length=100)
    is_locked = models.BooleanField(default=False)
    status = models.CharField(max_length=10, default='Active')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = 'acc_coa_level2'
        ordering = ['account_id']

    def __str__(self):
        return f"{self.account_id} - {self.account_name}"


class AccCoaLevel3(models.Model):
    level2 = models.ForeignKey(AccCoaLevel2, models.DO_NOTHING)
    account_id = models.CharField(unique=True, max_length=6)
    account_name = models.CharField(max_length=120)
    is_locked = models.BooleanField(default=False)
    status = models.CharField(max_length=10, default='Active')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = 'acc_coa_level3'
        ordering = ['account_id']

    def __str__(self):
        return f"{self.account_id} - {self.account_name}"

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


   
class AccFinancialYear(models.Model):
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'acc_financial_year'


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


class AccSchoolPostingConfig(models.Model):
    config_key = models.CharField(unique=True, max_length=100)
    config_name = models.CharField(max_length=150)
    account = models.ForeignKey(AccCoaLevel4, models.DO_NOTHING, to_field='account_id', blank=True, null=True)
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'acc_school_posting_config'


class AccVoucherDetail(models.Model):
    voucher = models.ForeignKey('AccVoucherMaster', models.DO_NOTHING)
    account = models.ForeignKey(AccCoaLevel4, models.DO_NOTHING, to_field='account_id')
    debit = models.DecimalField(max_digits=15, decimal_places=2)
    credit = models.DecimalField(max_digits=15, decimal_places=2)
    narration = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'acc_voucher_detail'


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


class AccVoucherSequence(models.Model):
    voucher_type = models.CharField(max_length=10)
    fiscal_year = models.CharField(max_length=10)
    last_sequence = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'acc_voucher_sequence'
        unique_together = (('voucher_type', 'fiscal_year'),)

class AccBankMaster(models.Model):
    account = models.ForeignKey('AccCoalevel4', models.DO_NOTHING, to_field='account_id')
    bank_name = models.CharField(max_length=150)
    branch_name = models.CharField(max_length=100, blank=True, null=True)
    branch_code = models.CharField(max_length=20, blank=True, null=True)
    account_title = models.CharField(max_length=150)
    account_number = models.CharField(max_length=100)
    iban = models.CharField(max_length=50, blank=True, null=True)
    swift_code = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    opening_balance = models.DecimalField(max_digits=18, decimal_places=2, default=0.00)

    class Meta:
        managed = False
        db_table = 'acc_bank_master'
        unique_together = (('account',),)
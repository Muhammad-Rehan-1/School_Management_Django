from django.db import models

from decimal import Decimal


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
    admission_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    transport_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    other_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    photo = models.ImageField(upload_to='students/photos/', blank=True, null=True)
    form_b_image = models.ImageField(upload_to='students/form_b/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

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
    photo = models.ImageField(upload_to='teachers/photos/', blank=True, null=True)
    cnic_photo = models.ImageField(upload_to='teachers/cnic/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

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
    photo = models.ImageField(upload_to='staff/photos/', blank=True, null=True)
    cnic_photo = models.ImageField(upload_to='staff/cnic/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'core_staff'

    def __str__(self):
        return f"{self.name} - {self.role} ({self.emp_id})"


# (Keep your existing CoreStudent, CoreTeacher, CoreStaff models above)

class CoreStudentFee(models.Model):
    STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Unpaid', 'Unpaid'),
        ('Partial', 'Partial'),
    ]

    PAYMENT_METHODS = [
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('EasyPaisa / JazzCash', 'EasyPaisa / JazzCash'),
        ('Cheque', 'Cheque'),
    ]

    challan_no = models.CharField(max_length=50, unique=True)
    student = models.ForeignKey('CoreStudent', on_delete=models.CASCADE, db_column='student_id')
    fee_month = models.IntegerField()  # 1 to 12
    fee_year = models.IntegerField()   # e.g., 2026
    
    tuition_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    transport_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    admission_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    other_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    fine = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    arrears = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Unpaid')
    
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS, null=True, blank=True)
    due_date = models.DateField()
    issued_date = models.DateField(auto_now_add=True)
    notes = models.CharField(max_length=250, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'core_studentfee'

    def __str__(self):
        return f"{self.challan_no} - {self.student.name} ({self.status})"

class CoreStudentFee(models.Model):
    STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Unpaid', 'Unpaid'),
        ('Partial', 'Partial'),
    ]

    PAYMENT_METHODS = [
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('EasyPaisa / JazzCash', 'EasyPaisa / JazzCash'),
        ('Cheque', 'Cheque'),
    ]

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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Unpaid')
    
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS, null=True, blank=True)
    due_date = models.DateField()
    issued_date = models.DateField(auto_now_add=True)
    notes = models.CharField(max_length=250, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'core_studentfee'

    def __str__(self):
        return f"{self.challan_no} - {self.student.name} ({self.status})"
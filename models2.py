# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


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

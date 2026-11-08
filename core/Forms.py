from django import forms
from .models import Student


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            "name",
            "father_name",
            "student_class",
            "roll_no",
            "dob",
            "enrolment_date",
            "gender",
            "contact",
        ]
        widgets = {
            "dob": forms.DateInput(attrs={"type": "date"}),
            "enrolment_date": forms.DateInput(attrs={"type": "date"}),
        }
from django import forms

from .models import Rider


class RiderForm(forms.ModelForm):
    class Meta:
        model = Rider
        fields = ["name", "email", "mobile", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Full name"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "rider@example.com"}),
            "mobile": forms.TextInput(attrs={"class": "form-control", "placeholder": "9876543210"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

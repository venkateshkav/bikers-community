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


class RiderImportForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV file",
        widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".csv"}),
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data["csv_file"]
        if not csv_file.name.lower().endswith(".csv"):
            raise forms.ValidationError("Please upload a .csv file.")
        return csv_file

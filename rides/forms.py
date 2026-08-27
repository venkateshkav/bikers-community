from django import forms

from riders.models import Rider

from .models import Ride, RideRegistration


class RideForm(forms.ModelForm):
    class Meta:
        model = Ride
        fields = [
            "name",
            "start_location",
            "destination",
            "start_date",
            "start_time",
            "end_date",
            "end_time",
            "status",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Pondicherry Weekend Ride"}),
            "start_location": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. OMR Toll Gate"}),
            "destination": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Pondicherry Beach"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "start_time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", "End date cannot be before the start date.")
        return cleaned_data


class AddRiderToRideForm(forms.Form):
    rider = forms.ModelChoiceField(queryset=Rider.objects.none(), widget=forms.Select(attrs={"class": "form-select"}))
    auto_approve = forms.BooleanField(
        required=False, initial=True, label="Approve immediately", widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )

    def __init__(self, ride, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Riders with a REJECTED/CANCELLED registration may be re-added; only
        # a currently active (pending/approved) registration blocks re-adding.
        active_statuses = [RideRegistration.Status.PENDING, RideRegistration.Status.APPROVED]
        already_active = RideRegistration.objects.filter(ride=ride, status__in=active_statuses).values_list(
            "rider_id", flat=True
        )
        self.fields["rider"].queryset = Rider.objects.filter(is_active=True).exclude(id__in=already_active)

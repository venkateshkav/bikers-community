from django import forms

from riders.models import Rider

from .models import Ride, RideRegistration


class RideForm(forms.ModelForm):
    class Meta:
        model = Ride
        fields = [
            "name",
            "ride_date",
            "start_location",
            "destination",
            "start_time",
            "expected_arrival_time",
            "expected_return_time",
            "description",
            "status",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Pondicherry Weekend Ride"}),
            "ride_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "start_location": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. OMR Toll Gate"}),
            "destination": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Pondicherry Beach"}),
            "start_time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "expected_arrival_time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "expected_return_time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


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

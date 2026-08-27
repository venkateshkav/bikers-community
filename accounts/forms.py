from django import forms


class EmailLoginForm(forms.Form):
    email = forms.EmailField(
        label="Registered email",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "you@example.com",
                "autofocus": True,
                "autocomplete": "email",
                "inputmode": "email",
            }
        ),
    )

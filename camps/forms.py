"""Form for creating and editing camps (SPEC §9.2)."""

from django import forms
from django.forms import BoundField

from camps.models import Camp

SECTIONS = [
    ("Camp", ["chiro", "name", "start_date", "end_date"]),
    ("Headcount", ["num_children", "num_teens", "num_staff"]),
    (
        "Meal times",
        ["breakfast_time", "lunch_time", "teatime_time", "dinner_time"],
    ),
    (
        "Runbook info",
        [
            "cook_team",
            "location",
            "contact_leader",
            "contact_rental",
            "bakery",
            "general_notes",
        ],
    ),
]


def _date_input() -> forms.DateInput:
    return forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


def _time_input() -> forms.TimeInput:
    return forms.TimeInput(attrs={"type": "time"}, format="%H:%M")


class CampForm(forms.ModelForm):
    class Meta:
        model = Camp
        fields = [name for _, names in SECTIONS for name in names]
        widgets = {
            "start_date": _date_input(),
            "end_date": _date_input(),
            "breakfast_time": _time_input(),
            "lunch_time": _time_input(),
            "teatime_time": _time_input(),
            "dinner_time": _time_input(),
            "cook_team": forms.Textarea(attrs={"rows": 3}),
            "location": forms.Textarea(attrs={"rows": 2}),
            "contact_leader": forms.Textarea(attrs={"rows": 2}),
            "contact_rental": forms.Textarea(attrs={"rows": 2}),
            "bakery": forms.Textarea(attrs={"rows": 2}),
            "general_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Moving a camp to another Chiro would take it from its members.
            del self.fields["chiro"]
            return
        chiros = user.chiros.all()
        self.fields["chiro"].queryset = chiros
        if len(chiros) == 1:
            self.fields["chiro"].initial = chiros[0]
            self.fields["chiro"].widget = forms.HiddenInput()

    def sections(self) -> list[tuple[str, list[BoundField]]]:
        return [
            (title, [self[name] for name in names if name in self.fields])
            for title, names in SECTIONS
        ]

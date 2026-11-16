"""Form for creating and editing camps (docs/spec/planning.md)."""

from django import forms
from django.forms import BoundField, modelformset_factory
from django.utils.translation import gettext_lazy as _

from camps.models import Camp, CampGroup, DietaryNeed
from core.rows import UniqueRowsFormSet

SECTIONS = [
    (_("Camp"), ["chiro", "name", "start_date", "end_date"]),
    (
        _("Meal times"),
        ["breakfast_time", "lunch_time", "teatime_time", "dinner_time"],
    ),
    (
        _("Runbook info"),
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


class _DietaryNeedFormSet(UniqueRowsFormSet):
    unique_field = "diet"


DietaryNeedFormSet = modelformset_factory(
    DietaryNeed,
    formset=_DietaryNeedFormSet,
    fields=["diet", "count", "note"],
    extra=2,
    can_delete=True,
)


# A new camp starts with the usual Chiro afdelingen and teams, when its Chiro has no
# earlier camp to copy them from. Stored as typed, so in Dutch. Rows left at 0
# aren't saved.
DEFAULT_GROUPS: list[tuple[str, str]] = [
    ("Ribbels", CampGroup.Kind.CHILDREN),
    ("Speelclub", CampGroup.Kind.CHILDREN),
    ("Rakwi's", CampGroup.Kind.CHILDREN),
    ("Tito's", CampGroup.Kind.TEENS),
    ("Keti's", CampGroup.Kind.TEENS),
    ("Aspi's", CampGroup.Kind.TEENS),
    ("Leiding", CampGroup.Kind.STAFF),
    ("Kookploeg", CampGroup.Kind.STAFF),
    ("Technische ploeg", CampGroup.Kind.STAFF),
]


class _CampGroupFormSet(UniqueRowsFormSet):
    unique_field = "name"


def camp_group_formset(
    data=None, *, camp: Camp, initial: list[dict] | None = None
) -> UniqueRowsFormSet:
    """The camp's groups, with the initial rows (a new camp) or one empty row."""
    formset_class = modelformset_factory(
        CampGroup,
        formset=_CampGroupFormSet,
        fields=["name", "kind", "count"],
        widgets={"count": forms.NumberInput(attrs={"min": 0, "data-group-count": ""})},
        extra=len(initial) if initial else 1,
        can_delete=True,
    )
    queryset = camp.groups.all() if camp.pk else CampGroup.objects.none()
    return formset_class(data, queryset=queryset, initial=initial, prefix="groups")


def initial_groups(user) -> list[dict]:
    """The rows a new camp starts with: the groups of the latest camp of the user's
    Chiro, with the numbers left for this camp, or else the usual afdelingen."""
    chiros = list(user.chiros.all())
    if len(chiros) == 1:
        latest = chiros[0].camps.filter(groups__isnull=False).first()
        if latest:
            return [
                {"name": group.name, "kind": group.kind, "count": 0}
                for group in latest.groups.all()
            ]
    return [{"name": name, "kind": kind, "count": 0} for name, kind in DEFAULT_GROUPS]

"""The Chiro's stock and a camp's needs, both edited as a table
(docs/spec/kitchen.md)."""

from django import forms
from django.core.exceptions import ValidationError
from django.forms import (
    BaseFormSet,
    BaseModelFormSet,
    formset_factory,
    modelformset_factory,
)
from django.utils.translation import gettext_lazy as _

from kitchen.models import Utensil

# The <datalist> the needs table suggests names from.
NAMES_LIST_ID = "utensil-names"


def _check_unique_names(formset: BaseFormSet) -> list[forms.Form]:
    """Names are compared without case: "Kookpot" and "kookpot" are one item."""
    seen = set()
    kept = []
    for form in formset.forms:
        if formset._should_delete_form(form) or not hasattr(form, "cleaned_data"):
            continue
        name = (form.cleaned_data.get("name") or "").strip()
        if not name:
            continue
        if name.lower() in seen:
            raise ValidationError(_("%(name)s is in the list twice.") % {"name": name})
        seen.add(name.lower())
        kept.append(form)
    return kept


class _StockFormSet(BaseModelFormSet):
    def clean(self) -> None:
        super().clean()
        _check_unique_names(self)
        for form in self.forms:
            utensil = form.instance
            if not (utensil.pk and self._should_delete_form(form)):
                continue
            camps = sorted({need.camp.name for need in utensil.camp_needs.all()})
            if camps:
                raise ValidationError(
                    _("%(name)s is still needed by %(camps)s.")
                    % {"name": utensil.name, "camps": ", ".join(camps)}
                )


StockFormSet = modelformset_factory(
    Utensil,
    formset=_StockFormSet,
    fields=["name", "in_stock", "note"],
    extra=3,
    can_delete=True,
)


class NeedForm(forms.Form):
    name = forms.CharField(
        max_length=200,
        label=_("Kitchen utility"),
        widget=forms.TextInput(attrs={"list": NAMES_LIST_ID}),
    )
    needed = forms.IntegerField(min_value=1, initial=1, label=_("Needed"))


class _NeedFormSet(BaseFormSet):
    def clean(self) -> None:
        super().clean()
        self.kept_forms = _check_unique_names(self)


NeedFormSet = formset_factory(NeedForm, formset=_NeedFormSet, extra=3, can_delete=True)

"""Editable tables where each row must be about something different."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms import BaseModelFormSet
from django.utils.translation import gettext as _

MAX_ROW_INDEX = 1000


def row_index(total_forms: str | None) -> int:
    """The next row's index: the TOTAL_FORMS the page sent, bounded."""
    try:
        index = int(total_forms or 0)
    except ValueError:
        return 0
    return max(0, min(index, MAX_ROW_INDEX))


class UniqueRowsFormSet(BaseModelFormSet):
    """The database only allows one row per `unique_field` for a parent, which the
    forms can't check because the parent isn't one of their fields."""

    unique_field = ""

    def clean(self) -> None:
        super().clean()
        seen = set()
        for form in self.forms:
            # Not deleted_forms: that is empty while any other row is invalid.
            if self._should_delete_form(form) or not hasattr(form, "cleaned_data"):
                continue
            value = form.cleaned_data.get(self.unique_field)
            if value in seen:
                raise ValidationError(
                    _("%(name)s is in the list twice.") % {"name": value}
                )
            if value:
                seen.add(value)

    @transaction.atomic
    def save_rows(self, **parent) -> None:
        """Saving row by row would trip over the unique constraint halfway when two
        rows swap values, or a removed value is added again. So changed rows leave
        first, and go back in with their own ids."""
        rows = self.save(commit=False)
        for row in self.deleted_objects:
            row.delete()
        self.model.objects.filter(pk__in=[row.pk for row in rows if row.pk]).delete()
        for row in rows:
            for field, value in parent.items():
                setattr(row, field, value)
            row.save()

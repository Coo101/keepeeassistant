"""The pantry moves from the camp to its Chiro (SPEC §9.12). Items of several camps
of one Chiro become one item each, with their quantities added up."""

import django.db.models.deletion
from django.db import migrations, models


def to_chiro(apps, schema_editor) -> None:
    PantryItem = apps.get_model("shopping", "PantryItem")
    kept = {}
    for item in PantryItem.objects.select_related("camp").order_by("pk"):
        key = (item.camp.chiro_id, item.ingredient_id)
        if key in kept:
            kept[key].quantity += item.quantity
            kept[key].save(update_fields=["quantity"])
            item.delete()
        else:
            item.chiro_id = item.camp.chiro_id
            item.save(update_fields=["chiro"])
            kept[key] = item


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_chiro_is_example"),
        ("shopping", "0003_translated_labels"),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="pantryitem", name="unique_pantry_item"),
        migrations.AddField(
            model_name="pantryitem",
            name="chiro",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="pantry_items",
                to="accounts.chiro",
            ),
        ),
        migrations.RunPython(to_chiro, migrations.RunPython.noop),
        migrations.RemoveField(model_name="pantryitem", name="camp"),
        migrations.AlterField(
            model_name="pantryitem",
            name="chiro",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="pantry_items",
                to="accounts.chiro",
            ),
        ),
        migrations.AddConstraint(
            model_name="pantryitem",
            constraint=models.UniqueConstraint(
                fields=("chiro", "ingredient"), name="unique_pantry_item"
            ),
        ),
    ]

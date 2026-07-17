"""Remap consolidated dish types: breakfast -> bread_meal,
breakfast_extra -> bread_meal_extra, main -> hot_meal."""

from django.db import migrations

REMAP = {
    "breakfast": "bread_meal",
    "breakfast_extra": "bread_meal_extra",
    "main": "hot_meal",
}


def forwards(apps, schema_editor):
    recipe_model = apps.get_model("recipes", "Recipe")
    for old, new in REMAP.items():
        recipe_model.objects.filter(dish_type=old).update(dish_type=new)


def backwards(apps, schema_editor):
    # Lossy: former breakfast and bread_meal rows are indistinguishable,
    # as are former main and hot_meal rows. Leave data as-is.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("recipes", "0004_alter_recipe_dish_type"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

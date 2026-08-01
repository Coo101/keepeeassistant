"""Rename price_product -> product_details, add shop, mark loose products."""

from django.db import migrations, models


def mark_loose(apps, schema_editor):
    ingredient_model = apps.get_model("recipes", "Ingredient")
    for ingredient in ingredient_model.objects.filter(
        product_details__contains="[]"
    ):
        ingredient.product_details = ingredient.product_details.replace(
            "[]", "[LOS]"
        )
        ingredient.save(update_fields=["product_details"])


class Migration(migrations.Migration):
    dependencies = [
        ("recipes", "0006_ingredient_colruyt_product_id_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="ingredient",
            old_name="price_product",
            new_name="product_details",
        ),
        migrations.AlterField(
            model_name="ingredient",
            name="product_details",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Name, [brand] ([LOS] = loose/unpackaged) and container "
                    "volume or other details"
                ),
                max_length=200,
                verbose_name="product details",
            ),
        ),
        migrations.AddField(
            model_name="ingredient",
            name="shop",
            field=models.CharField(
                choices=[
                    ("vanzon", "Van Zon"),
                    ("colruyt", "Colruyt"),
                    ("bakker", "Bakker"),
                    ("beenhouwer", "Beenhouwer"),
                ],
                default="colruyt",
                help_text=(
                    "Where this ingredient is bought; only Colruyt items "
                    "get automatic price updates"
                ),
                max_length=12,
            ),
        ),
        migrations.RunPython(mark_loose, migrations.RunPython.noop),
    ]

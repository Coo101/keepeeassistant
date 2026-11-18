"""Bills are PDFs with text, read in Python (D21): the AI reader and its "waiting"
status are gone. Bills still waiting become "couldn't be read", lines kept."""

from django.db import migrations, models

WAITING_ERROR = "Waiting for the AI reader, which is gone: add the lines by hand."


def waiting_to_failed(apps, schema_editor):
    Bill = apps.get_model("bills", "Bill")
    Bill.objects.filter(status="waiting").update(status="failed", error=WAITING_ERROR)


class Migration(migrations.Migration):

    dependencies = [
        ("bills", "0004_kitchen_utilities"),
    ]

    operations = [
        migrations.RunPython(waiting_to_failed, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="bill",
            name="status",
            field=models.CharField(
                choices=[
                    ("failed", "Couldn't be read"),
                    ("review", "To review"),
                    ("done", "Reviewed"),
                ],
                default="review",
                max_length=10,
                verbose_name="status",
            ),
        ),
    ]

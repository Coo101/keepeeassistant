"""Give every camp a Chiro. Existing camps and users go into one placeholder
Chiro, to be renamed in the admin, so nobody loses access to their camps."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def assign_existing_camps(apps, schema_editor) -> None:
    Camp = apps.get_model("camps", "Camp")
    if not Camp.objects.exists():
        return
    Chiro = apps.get_model("accounts", "Chiro")
    Membership = apps.get_model("accounts", "Membership")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    chiro = Chiro.objects.create(name="Mijn Chiro")
    Camp.objects.update(chiro=chiro)
    Membership.objects.bulk_create(
        Membership(user=user, chiro=chiro) for user in User.objects.all()
    )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("camps", "0002_camp_bakery_camp_contact_leader_camp_contact_rental_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="camp",
            name="chiro",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="camps",
                to="accounts.chiro",
            ),
        ),
        migrations.RunPython(assign_existing_camps, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="camp",
            name="chiro",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="camps",
                to="accounts.chiro",
            ),
        ),
    ]

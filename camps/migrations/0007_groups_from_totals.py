"""Give every existing camp groups that add up to its current totals, so saving
the camp form keeps them. People split them into afdelingen afterwards."""

from django.db import migrations

# Stored data, so in the language the users write in (SPEC §10).
NAMES = {
    "children": "Kinderen -12 (nog te verdelen)",
    "teens": "Leden 12+ (nog te verdelen)",
    "staff": "Leiding en ploegen (nog te verdelen)",
}


def groups_from_totals(apps, schema_editor) -> None:
    Camp = apps.get_model("camps", "Camp")
    CampGroup = apps.get_model("camps", "CampGroup")
    for camp in Camp.objects.all():
        if CampGroup.objects.filter(camp=camp).exists():
            continue
        counts = {
            "children": camp.num_children,
            "teens": camp.num_teens,
            "staff": camp.num_staff,
        }
        CampGroup.objects.bulk_create(
            CampGroup(camp=camp, name=NAMES[kind], kind=kind, count=count)
            for kind, count in counts.items()
            if count
        )


class Migration(migrations.Migration):
    dependencies = [("camps", "0006_camp_groups")]

    operations = [
        migrations.RunPython(groups_from_totals, migrations.RunPython.noop),
    ]

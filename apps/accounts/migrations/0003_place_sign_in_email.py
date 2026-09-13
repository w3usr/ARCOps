# Existing accounts get their sign-in address placed into a contact slot the way new accounts do
# from now on (services.place_sign_in_email): the institution slot when the domain matches the
# one the club configures for its institution, otherwise the personal slot, and only when empty.

from django.db import migrations


def institution_domain(apps) -> str:
    ClubSetting = apps.get_model("ops", "ClubSetting")
    try:
        cats = ClubSetting.objects.get(key="member_categories").value or []
    except ClubSetting.DoesNotExist:
        return ""
    for c in cats:
        if isinstance(c, dict) and c.get("email_domain"):
            return str(c["email_domain"]).lower()
    return ""


def place(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    inst = institution_domain(apps)
    for u in User.objects.all():
        if not u.email:
            continue
        domain = u.email.rsplit("@", 1)[-1].lower()
        if inst and domain == inst:
            if not u.institution_email:
                u.institution_email = u.email
                u.save(update_fields=["institution_email"])
        elif not u.personal_email:
            u.personal_email = u.email
            u.save(update_fields=["personal_email"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_email_delivery_switches"),
        ("ops", "0001_initial"),
    ]
    operations = [migrations.RunPython(place, migrations.RunPython.noop)]

import os

from django.contrib.auth.models import User
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("frontend", "0001_initial")]

    def generate_superuser(apps, schema_editor):
        USER = os.environ.get("DJANGO_SU_NAME")
        PASSWD = os.environ.get("DJANGO_SU_PASSWD")
        EMAIL = os.environ.get("DJANGO_SU_EMAIL")

        superuser = User.objects.create_superuser(username=USER, password=PASSWD, email=EMAIL)
        superuser.save()

    operations = [migrations.RunPython(generate_superuser)]

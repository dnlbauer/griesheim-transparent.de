# Generated by Django 4.1.1 on 2023-04-16 19:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ris', '0003_alter_organization_organization_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organization',
            name='name',
            field=models.TextField(unique=True),
        ),
    ]
# Generated by Django 4.1.1 on 2023-04-23 20:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0004_query_page'),
    ]

    operations = [
        migrations.AddField(
            model_name='query',
            name='num_results',
            field=models.IntegerField(null=True),
        ),
    ]

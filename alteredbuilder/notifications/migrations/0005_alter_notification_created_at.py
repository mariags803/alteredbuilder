# Generated by Django 5.0.8 on 2024-08-08 16:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0004_alter_notification_actor_alter_notification_verb"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="created_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]

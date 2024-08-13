# Generated by Django 5.0.8 on 2024-08-12 15:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0005_alter_notification_created_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="verb",
            field=models.CharField(
                choices=[("comment", "Comment"), ("deck", "Deck"), ("love", "Love")]
            ),
        ),
    ]

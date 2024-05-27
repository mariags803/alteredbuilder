# Generated by Django 5.0.3 on 2024-05-27 15:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("decks", "0016_card_image_url_en_card_image_url_es_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="character",
            name="echo_effect_en",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="character",
            name="echo_effect_es",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="character",
            name="echo_effect_fr",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="character",
            name="main_effect_en",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="character",
            name="main_effect_es",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="character",
            name="main_effect_fr",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="permanent",
            name="echo_effect_en",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="permanent",
            name="echo_effect_es",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="permanent",
            name="echo_effect_fr",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="permanent",
            name="main_effect_en",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="permanent",
            name="main_effect_es",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="permanent",
            name="main_effect_fr",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="spell",
            name="echo_effect_en",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="spell",
            name="echo_effect_es",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="spell",
            name="echo_effect_fr",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="spell",
            name="main_effect_en",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="spell",
            name="main_effect_es",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="spell",
            name="main_effect_fr",
            field=models.TextField(blank=True, null=True),
        ),
    ]

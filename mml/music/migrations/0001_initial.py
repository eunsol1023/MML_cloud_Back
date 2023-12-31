# Generated by Django 4.2.7 on 2023-11-29 09:10

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="MMLMusicTagHis",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("artist", models.CharField(max_length=255)),
                ("image", models.CharField(max_length=2000)),
                ("user_id", models.CharField(max_length=255)),
                ("input_sentence", models.CharField(max_length=300)),
            ],
            options={
                "db_table": "mml_music_tag_his",
            },
        ),
    ]

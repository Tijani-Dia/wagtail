# Generated by Django 3.0.3 on 2021-03-05 17:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0060_comment_commentposition_commentreply'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='position',
            field=models.TextField(blank=True),
        ),
        migrations.DeleteModel(
            name='CommentPosition',
        ),
    ]

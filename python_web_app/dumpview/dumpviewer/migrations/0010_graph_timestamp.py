# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-02-16 06:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dumpviewer', '0009_remove_graph_timestamp'),
    ]

    operations = [
        migrations.AddField(
            model_name='graph',
            name='timestamp',
            field=models.TextField(default=None),
        ),
    ]

# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-04-19 23:18
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf_models', '0005_auto_20160419_1816'),
    ]

    operations = [
        migrations.AlterField(
            model_name='node',
            name='forked_date',
            field=models.DateTimeField(db_index=True, null=True),
        ),
    ]
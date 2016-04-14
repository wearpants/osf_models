# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-04-14 13:53
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import osf_models.models.base
import osf_models.models.validators
import osf_models.utils.datetime_aware_jsonfield


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BlackListGuid',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('guid', models.CharField(db_index=True, max_length=255, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Guid',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('guid', models.CharField(db_index=True, default=osf_models.models.base.generate_guid, max_length=255, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Node',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('is_public', models.BooleanField(db_index=True, default=False)),
                ('is_bookmark_collection', models.BooleanField(db_index=True, default=False)),
                ('is_collection', models.BooleanField(db_index=True, default=False)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('deleted_date', models.DateTimeField()),
                ('is_registration', models.BooleanField(db_index=True, default=False)),
                ('registered_date', models.DateTimeField(db_index=True)),
                ('registered_meta', osf_models.utils.datetime_aware_jsonfield.DatetimeAwareJSONField()),
                ('is_fork', models.BooleanField(db_index=True, default=False)),
                ('forked_date', models.DateTimeField(db_index=True)),
                ('title', models.CharField(max_length=200, validators=[osf_models.models.validators.validate_title])),
                ('description', models.TextField()),
                ('public_comments', models.BooleanField(default=True)),
                ('wiki_pages_current', osf_models.utils.datetime_aware_jsonfield.DatetimeAwareJSONField()),
                ('wiki_pages_versions', osf_models.utils.datetime_aware_jsonfield.DatetimeAwareJSONField()),
                ('wiki_private_uuids', osf_models.utils.datetime_aware_jsonfield.DatetimeAwareJSONField()),
                ('file_guid_to_share_uuids', osf_models.utils.datetime_aware_jsonfield.DatetimeAwareJSONField()),
                ('piwik_site_id', models.IntegerField()),
                ('child_node_subscriptions', osf_models.utils.datetime_aware_jsonfield.DatetimeAwareJSONField()),
                ('_guid', models.OneToOneField(default=osf_models.models.base.generate_guid_instance, on_delete=django.db.models.deletion.CASCADE, related_name='referent_node', to='osf_models.Guid')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='NodeLog',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('guid', models.CharField(db_index=True, max_length=255, unique=True)),
                ('node', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='osf_models.Node')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Permissions',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('read', models.BooleanField(default=False)),
                ('write', models.BooleanField(default=False)),
                ('admin', models.BooleanField(default=False)),
                ('node', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='osf_models.Node')),
            ],
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('_id', models.CharField(db_index=True, max_length=128)),
                ('lower', models.CharField(db_index=True, max_length=128)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('_guid', models.OneToOneField(default=osf_models.models.base.generate_guid_instance, on_delete=django.db.models.deletion.CASCADE, related_name='referent_user', to='osf_models.Guid')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='permissions',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='osf_models.User'),
        ),
        migrations.AddField(
            model_name='nodelog',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='osf_models.User'),
        ),
        migrations.AddField(
            model_name='node',
            name='contributors',
            field=models.ManyToManyField(related_name='contributed_to', through='osf_models.Permissions', to='osf_models.User'),
        ),
        migrations.AddField(
            model_name='node',
            name='creator',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created', to='osf_models.User'),
        ),
        migrations.AddField(
            model_name='node',
            name='forked_from',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='forks', to='osf_models.Node'),
        ),
        migrations.AddField(
            model_name='node',
            name='nodes',
            field=models.ManyToManyField(related_name='_node_nodes_+', to='osf_models.Node'),
        ),
        migrations.AddField(
            model_name='node',
            name='parent_node',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='parent', to='osf_models.Node'),
        ),
        migrations.AddField(
            model_name='node',
            name='registered_from',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='registrations', to='osf_models.Node'),
        ),
        migrations.AddField(
            model_name='node',
            name='registered_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='related_to', to='osf_models.User'),
        ),
        migrations.AddField(
            model_name='node',
            name='root',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='absolute_parent', to='osf_models.Node'),
        ),
        migrations.AddField(
            model_name='node',
            name='system_tags',
            field=models.ManyToManyField(related_name='tagged_by_system', to='osf_models.Tag'),
        ),
        migrations.AddField(
            model_name='node',
            name='tags',
            field=models.ManyToManyField(related_name='tagged', to='osf_models.Tag'),
        ),
        migrations.AddField(
            model_name='node',
            name='template_node',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='templated_from', to='osf_models.Node'),
        ),
        migrations.AddField(
            model_name='node',
            name='users_watching_node',
            field=models.ManyToManyField(related_name='watching', to='osf_models.User'),
        ),
    ]
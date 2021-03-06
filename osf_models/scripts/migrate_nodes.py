from __future__ import unicode_literals

import functools
import gc
import operator
import sys
from datetime import datetime

import pytz
from django.db import transaction
from framework.auth import User as MODMUser
from modularodm import Q as MQ
from osf_models.models import Contributor, Guid, Node, Tag, User
from osf_models.models.sanctions import Embargo
from website.models import Embargo as MODMEmbargo
from website.models import Node as MODMNode
from website.models import Tag as MODMTag
from website.project.model import Pointer


class DryMigrationException(BaseException):
    pass


fk_node_fields = [
    'forked_from', 'registered_from', 'root', 'parent_node', 'template_node',
    '_primary_institution', 'embargo'
]
m2m_node_fields = ['nodes', '_affiliated_institutions']
fk_user_fields = ['registered_user', 'creator', 'merged_by']
m2m_user_fields = [
    'permissions',
    'recently_added',
    'users_watching_node',
    'contributors',
]
m2m_tag_fields = ['tags', 'system_tags']

node_key_blacklist = [
    '__backrefs',
    '_version',
    'expanded',
    # foreign keys not yet implemented
    'logs',
    'primary_institution',
    #  '_primary_institution',
    #  'institution_email_domains',
    #  'institution_domains',
    'registration_approval',
    'alternative_citations',
    'registered_schema',
    'affiliated_institutions',
    #  '_affiliated_institutions',
    #  'institution_banner_name',
    #  'institution_id',
    #  'institution_auth_url',
    #  'institution_logo_name',
    'contributors',  # done elsewhere
    'retraction',
    # 'embargo',
    'node_license',
    'embargo_termination_approval',
] + fk_user_fields + fk_node_fields + m2m_node_fields + m2m_user_fields + m2m_tag_fields
user_key_blacklist = [
    '__backrefs',
    '_version',
    'affiliated_institutions',
    # '_affiliated_institutions',
    'watched',
    'external_accounts',
    'email_last_sent',
] + fk_user_fields + fk_node_fields + m2m_node_fields + m2m_user_fields + m2m_tag_fields


def build_query(fields, model):
    queries = (MQ(field, 'ne', None)
               for field in list(set(fields) & set(model._fields.keys())))
    if queries == []:
        return None
    return functools.reduce(operator.and_, queries)


def save_bare_nodes(page_size=20000):
    print 'Starting {}...'.format(sys._getframe().f_code.co_name)
    count = 0
    start = datetime.now()
    total = MODMNode.find(allow_institution=True).count()
    while count < total:
        with transaction.atomic():
            nids = []
            for modm_node in MODMNode.find(
                    allow_institution=True).sort('-date_modified')[
                        count:count + page_size]:
                guid = Guid.objects.get(guid=modm_node._id)
                node_fields = dict(_guid_id=guid.pk, **modm_node.to_storage())

                # remove fields not yet implemented
                cleaned_node_fields = {key: node_fields[key]
                                       for key in node_fields
                                       if key not in node_key_blacklist}

                # make datetimes not naive
                for k, v in cleaned_node_fields.iteritems():
                    if isinstance(v, datetime):
                        cleaned_node_fields[k] = pytz.utc.localize(v)

                # remove null fields, postgres hate null fields
                cleaned_node_fields = {k: v
                                       for k, v in
                                       cleaned_node_fields.iteritems()
                                       if v is not None}
                nids.append(Node(**cleaned_node_fields))
                count += 1
                if count % page_size == 0 or count == total:
                    then = datetime.now()
                    print 'Saving nodes {} through {}...'.format(
                        count - page_size, count)
                    woot = Node.objects.bulk_create(nids)
                    for wit in woot:
                        modm_to_django[wit._guid.guid] = wit.pk
                    now = datetime.now()
                    print 'Done with {} nodes in {} seconds...'.format(
                        len(woot), (now - then).total_seconds())
                    nids = []
                    trash = gc.collect()
                    print 'Took out {} trashes'.format(trash)

    print 'Modm Nodes: {}'.format(total)
    print 'django Nodes: {}'.format(Node.objects.all().count())
    print 'Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds())


def save_bare_users(page_size=20000):
    print 'Starting {}...'.format(sys._getframe().f_code.co_name)
    count = 0
    start = datetime.now()
    total = MODMUser.find().count()

    while count < total:
        with transaction.atomic():
            users = []
            for modm_user in MODMUser.find().sort('-date_registered')[
                    count:count + page_size]:
                guid = Guid.objects.get(guid=modm_user._id)
                user_fields = dict(_guid_id=guid.pk, **modm_user.to_storage())

                cleaned_user_fields = {key: user_fields[key]
                                       for key in user_fields
                                       if key not in user_key_blacklist}

                for k, v in cleaned_user_fields.iteritems():
                    if isinstance(v, datetime):
                        cleaned_user_fields[k] = pytz.utc.localize(v)

                cleaned_user_fields = {k: v
                                       for k, v in
                                       cleaned_user_fields.iteritems()
                                       if v is not None}
                users.append(User(**cleaned_user_fields))
                count += 1
                if count % page_size == 0 or count == total:
                    then = datetime.now()
                    print 'Saving users {} through {}...'.format(
                        count - page_size, count)
                    woot = User.objects.bulk_create(users)
                    for wit in woot:
                        modm_to_django[wit._guid.guid] = wit.pk
                    now = datetime.now()
                    print 'Done with {} users in {} seconds...'.format(
                        len(woot), (now - then).total_seconds())
                    users = None
                    woot = None
                    guid = None
                    user_fields = None
                    cleaned_user_fields = None
                    trash = gc.collect()
                    print 'Took out {} trashes'.format(trash)

    print 'Modm Users: {}'.format(total)
    print 'django Users: {}'.format(User.objects.all().count())
    print 'Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds())


def save_bare_tags(page_size=5000):
    print 'Starting {}...'.format(sys._getframe().f_code.co_name)
    count = 0
    start = datetime.now()
    total = MODMTag.find().count()

    while count < total:
        with transaction.atomic():
            tags = []
            for modm_tag in MODMTag.find().sort('-_id')[count:count +
                                                        page_size]:
                tags.append(Tag(_id=modm_tag._id,
                                lower=modm_tag.lower,
                                system=False))
                count += 1
                if count % page_size == 0 or count == total:
                    then = datetime.now()
                    print 'Saving tags {} through {}...'.format(
                        count - page_size, count)
                    woot = Tag.objects.bulk_create(tags)
                    now = datetime.now()
                    print 'Done with {} tags in {} seconds...'.format(
                        len(woot), (now - then).total_seconds())
                    tags = None
                    woot = None
                    trash = gc.collect()
                    print 'Took out {} trashes'.format(trash)

    print 'MODM Tags: {}'.format(total)
    print 'django Tags: {}'.format(Tag.objects.all().count())
    print 'Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds())


def save_bare_system_tags(page_size=10000):
    print 'Starting save_bare_system_tags...'
    start = datetime.now()

    things = list(MODMNode.find(MQ('system_tags', 'ne', [])).sort(
        '-_id')) + list(MODMUser.find(MQ('system_tags', 'ne', [])).sort(
            '-_id'))

    system_tag_ids = []
    for thing in things:
        for system_tag in thing.system_tags:
            system_tag_ids.append(system_tag)

    unique_system_tag_ids = set(system_tag_ids)

    total = len(unique_system_tag_ids)

    system_tags = []
    for system_tag_id in unique_system_tag_ids:
        system_tags.append(Tag(_id=system_tag_id,
                               lower=system_tag_id.lower(),
                               system=True))

    woot = Tag.objects.bulk_create(system_tags)

    print 'MODM System Tags: {}'.format(total)
    print 'django system tags: {}'.format(Tag.objects.filter(system=
                                                             True).count())
    print 'Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds())


def save_bare_embargos(page_size=10000):
    print 'Starting {}...'.format(sys._getframe().f_code.co_name)
    embargo_key_blacklist = ['__backrefs', '_version', ]

    start = datetime.now()
    count = 0
    total = MODMEmbargo.find().count()

    while count < total:
        with transaction.atomic():
            embargos = []
            for modm_embargo in MODMEmbargo.find().sort('-_id')[count:count +
                                                                page_size]:
                embargo_fields = modm_embargo.to_storage()
                cleaned_embargo_fields = {key: embargo_fields[key]
                                          for key in embargo_fields
                                          if key not in (embargo_key_blacklist)
                                          }
                for k, v in cleaned_embargo_fields.iteritems():
                    if isinstance(v, datetime):
                        cleaned_embargo_fields[k] = pytz.utc.localize(v)

                try:
                    initiated_by_id = modm_to_django[cleaned_embargo_fields[
                        'initiated_by']]
                except KeyError:
                    print 'Couldn\'t find user with guid {}'.format()
                else:
                    cleaned_embargo_fields['initiated_by_id'] = initiated_by_id
                    del cleaned_embargo_fields['initiated_by']

                embargos.append(Embargo(**cleaned_embargo_fields))
                count += 1
                if count % page_size == 0 or count == total:
                    then = datetime.now()
                    print 'Saving embargos {} through {}...'.format(
                        count - page_size, count)
                    woot = Embargo.objects.bulk_create(embargos)
                    for wit in woot:
                        modm_to_django[wit.guid] = wit.pk
                    now = datetime.now()
                    print 'Done with {} embargos in {} seconds...'.format(
                        len(woot), (now - then).total_seconds())
                    embargos = None
                    woot = None
                    guid = None
                    embargo_fields = None
                    cleaned_embargo_fields = None
                    trash = gc.collect()
                    print 'Took out {} trashes'.format(trash)
    print 'Modm embargos: {}'.format(total)
    print 'django embargos: {}'.format(Embargo.objects.count())
    print 'Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds())


def set_node_foreign_keys_on_nodes(page_size=10000):
    print 'Starting {}...'.format(sys._getframe().f_code.co_name)
    node_count = 0
    fk_count = 0
    cache_hits = 0
    cache_misses = 0
    start = datetime.now()
    total = MODMNode.find(
        build_query(fk_node_fields, MODMNode),
        allow_institution=True).count()

    while node_count < total:
        with transaction.atomic():
            for modm_node in MODMNode.find(
                    build_query(fk_node_fields, MODMNode),
                    allow_institution=True).sort('-date_modified')[
                        node_count:node_count + page_size]:
                django_node = Node.objects.get(_guid__guid=modm_node._id)
                for fk_node_field in fk_node_fields:
                    value = getattr(modm_node, fk_node_field, None)
                    if value is not None:
                        if isinstance(value, basestring):
                            # value is a guid, try the cache table for the pk
                            if value in modm_to_django:
                                setattr(django_node,
                                        '{}_id'.format(fk_node_field),
                                        modm_to_django[value])
                                cache_hits += 1
                            else:
                                # it's not in the cache, do the query
                                node_id = Node.objects.get(
                                    _guid__guid=value).pk
                                setattr(django_node,
                                        '{}_id'.format(fk_node_field), node_id)
                                # save for later
                                modm_to_django[value] = node_id
                                cache_misses += 1
                        elif isinstance(value, MODMNode):
                            # value is a node object, try the cache table for the pk
                            if value._id in modm_to_django:
                                setattr(django_node,
                                        '{}_id'.format(fk_node_field),
                                        modm_to_django[value._id])
                                cache_hits += 1
                            else:
                                # it's not in the cache, do the query
                                node_id = Node.objects.get(
                                    _guid__guid=value._id).pk
                                setattr(django_node,
                                        '{}_id'.format(fk_node_field), node_id)
                                # save for later
                                modm_to_django[value._id] = node_id
                                cache_misses += 1
                        else:
                            # whu happened?
                            print '\a'
                            print '\a'
                            print '\a'
                            print '\a'
                            print '\a'
                            print '\a'
                            import bpdb
                            bpdb.set_trace()
                        fk_count += 1
                django_node.save()
                node_count += 1
                if node_count % page_size == 0 or node_count == total:
                    then = datetime.now()
                    print 'Through {} nodes and {} foreign keys'.format(
                        node_count, fk_count)
                    print 'Cache: Hits {} Misses {}'.format(cache_hits,
                                                            cache_misses)
    print 'Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds())


def set_user_foreign_keys_on_nodes(page_size=10000):
    print 'Starting {}...'.format(sys._getframe().f_code.co_name)
    node_count = 0
    fk_count = 0
    cache_hits = 0
    cache_misses = 0
    start = datetime.now()
    total = MODMNode.find(
        build_query(fk_user_fields, MODMNode),
        allow_institution=True).count()

    while node_count < total:
        with transaction.atomic():
            for modm_node in MODMNode.find(
                    build_query(fk_user_fields, MODMNode),
                    allow_institution=True).sort('-date_modified')[
                        node_count:node_count + page_size]:
                django_node = Node.objects.get(_guid__guid=modm_node._id)
                for fk_user_field in fk_user_fields:
                    value = getattr(modm_node, fk_user_field, None)
                    if value is not None:
                        if isinstance(value, basestring):
                            # value is a guid, try the cache table for the pk
                            if value in modm_to_django:
                                setattr(django_node,
                                        '{}_id'.format(fk_user_field),
                                        modm_to_django[value])
                                cache_hits += 1
                            else:
                                # it's not in the cache, do the query
                                user_id = User.objects.get(
                                    _guid__guid=value).pk
                                setattr(django_node,
                                        '{}_id'.format(fk_user_field), user_id)
                                # save for later
                                modm_to_django[value] = user_id
                                cache_misses += 1
                        elif isinstance(value, MODMUser):
                            # value is a node object, try the cache table for the pk
                            if value._id in modm_to_django:
                                setattr(django_node,
                                        '{}_id'.format(fk_user_field),
                                        modm_to_django[value._id])
                                cache_hits += 1
                            else:
                                # it's not in the cache, do the query
                                user_id = User.objects.get(
                                    _guid__guid=value._id).pk
                                setattr(django_node,
                                        '{}_id'.format(fk_user_field), user_id)
                                # save for later
                                modm_to_django[value._id] = user_id
                                cache_misses += 1
                        else:
                            # that's odd.
                            print '\a'
                            print '\a'
                            print '\a'
                            print '\a'
                            print '\a'
                            print '\a'
                            import bpdb
                            bpdb.set_trace()
                        fk_count += 1
                django_node.save()
                node_count += 1
                if node_count % page_size == 0 or node_count == total:
                    print 'Through {} nodes and {} foreign keys'.format(
                        node_count, fk_count)
                    print 'Cache: Hits {} Misses {}'.format(cache_hits,
                                                            cache_misses)
    print 'Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds())


def set_user_foreign_keys_on_users(page_size=10000):
    print 'Starting {}...'.format(sys._getframe().f_code.co_name)
    user_count = 0
    fk_count = 0
    cache_hits = 0
    cache_misses = 0
    start = datetime.now()
    total = MODMUser.find(build_query(fk_user_fields, MODMUser)).count()

    while user_count < total:
        with transaction.atomic():
            for modm_user in MODMUser.find(build_query(
                    fk_user_fields, MODMUser)).sort('-date_registered')[
                        user_count:user_count + page_size]:
                django_user = User.objects.get(_guid__guid=modm_user._id)
                for fk_user_field in fk_user_fields:
                    value = getattr(modm_user, fk_user_field, None)
                    if value is not None:
                        if isinstance(value, basestring):
                            # value is a guid, try the cache table for the pk
                            if value in modm_to_django:
                                setattr(django_user,
                                        '{}_id'.format(fk_user_field),
                                        modm_to_django[value])
                                cache_hits += 1
                            else:
                                # it's not in the cache, do the query
                                user_id = User.objects.get(
                                    _guid__guid=value).pk
                                setattr(django_user,
                                        '{}_id'.format(fk_user_field), user_id)
                                # save for later
                                modm_to_django[value] = user_id
                                cache_misses += 1
                        elif isinstance(value, MODMUser):
                            # value is a user object, try the cache table for the pk
                            if value._id in modm_to_django:
                                setattr(django_user,
                                        '{}_id'.format(fk_user_field),
                                        modm_to_django[value._id])
                                cache_hits += 1
                            else:
                                # it's not in the cache, do the query
                                user_id = User.objects.get(
                                    _guid__guid=value._id).pk
                                setattr(django_user,
                                        '{}_id'.format(fk_user_field), user_id)
                                # save for later
                                modm_to_django[value._id] = user_id
                                cache_misses += 1
                        else:
                            # that's odd.
                            print '\a'
                            print '\a'
                            print '\a'
                            print '\a'
                            print '\a'
                            print '\a'
                            import bpdb
                            bpdb.set_trace()
                        fk_count += 1
                django_user.save()
                user_count += 1
                if user_count % page_size == 0 or user_count == total:
                    print 'Through {} users and {} foreign keys'.format(
                        user_count, fk_count)
                    print 'Cache: Hits {} Misses {}'.format(cache_hits,
                                                            cache_misses)
    print 'Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds())


def set_node_many_to_many_on_nodes(page_size=5000):
    print 'Starting {}...'.format(sys._getframe().f_code.co_name)
    node_count = 0
    m2m_count = 0
    start = datetime.now()
    total = MODMNode.find(
        build_query(m2m_node_fields, MODMNode),
        allow_institution=True).count()
    print '{} Nodes'.format(total)
    while node_count < total:
        with transaction.atomic():
            for modm_node in MODMNode.find(
                    build_query(m2m_node_fields, MODMNode),
                    allow_institution=True).sort('-date_modified')[
                        node_count:page_size + node_count]:
                django_node = Node.objects.get(
                    pk=modm_to_django[modm_node._id])
                for m2m_node_field in m2m_node_fields:
                    attr = getattr(django_node, m2m_node_field)
                    django_pks = []
                    for modm_m2m_value in getattr(modm_node, m2m_node_field,
                                                  []):
                        if isinstance(modm_m2m_value, MODMNode):
                            django_pks.append(modm_to_django[
                                modm_m2m_value._id])
                        elif isinstance(modm_m2m_value, basestring):
                            django_pks.append(modm_to_django[modm_m2m_value])
                        elif isinstance(modm_m2m_value, Pointer):
                            django_pks.append(modm_to_django[
                                modm_m2m_value.node._id])
                        else:
                            # wth
                            print '\a'
                            print '\a'
                            print '\a'
                            print '\a'
                            print '\a'
                            print '\a'
                            print '\a'
                            import bpdb
                            bpdb.set_trace()
                    if len(django_pks) > 0:
                        attr.add(*django_pks)
                    m2m_count += len(django_pks)
                node_count += 1
                if node_count % page_size == 0 or node_count == total:
                    print 'Through {} nodes and {} m2m'.format(node_count,
                                                               m2m_count)
    print 'Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds())


def set_user_many_to_many_on_nodes(page_size=5000):
    print 'Starting {}...'.format(sys._getframe().f_code.co_name)
    node_count = 0
    m2m_count = 0
    start = datetime.now()
    total = MODMNode.find(
        build_query(m2m_user_fields, MODMNode),
        allow_institution=True).count()
    print '{} Nodes'.format(total)
    while node_count < total:
        with transaction.atomic():
            for modm_node in MODMNode.find(
                    build_query(m2m_user_fields, MODMNode),
                    allow_institution=True).sort('-date_modified')[
                        node_count:page_size + node_count]:
                django_node = Node.objects.get(
                    pk=modm_to_django[modm_node._id])
                for m2m_user_field in m2m_user_fields:
                    if m2m_user_field in ['permissions', 'recently_added']:
                        continue
                    attr = getattr(django_node, m2m_user_field)
                    django_pks = []
                    for modm_m2m_value in getattr(modm_node, m2m_user_field,
                                                  []):
                        if isinstance(modm_m2m_value, MODMUser):
                            if m2m_user_field == 'contributors':
                                visible = modm_m2m_value._id in modm_node.visible_contributor_ids
                                admin = 'admin' in modm_node.permissions[
                                    modm_m2m_value._id]
                                read = 'read' in modm_node.permissions[
                                    modm_m2m_value._id]
                                write = 'write' in modm_node.permissions[
                                    modm_m2m_value._id]

                                Contributor.objects.get_or_create(
                                    user_id=modm_to_django[modm_m2m_value._id],
                                    node=django_node,
                                    visible=visible,
                                    admin=admin,
                                    read=read,
                                    write=write)
                                m2m_count += 1
                            else:
                                django_pks.append(modm_to_django[
                                    modm_m2m_value._id])
                        elif isinstance(modm_m2m_value, basestring):
                            if m2m_user_field == 'contributors':
                                visible = modm_m2m_value in modm_node.visible_contributor_ids
                                admin = 'admin' in modm_node.permissions[
                                    modm_m2m_value]
                                read = 'read' in modm_node.permissions[
                                    modm_m2m_value]
                                write = 'write' in modm_node.permissions[
                                    modm_m2m_value]
                                Contributor.objects.get_or_create(
                                    user_id=modm_to_django[modm_m2m_value],
                                    node=django_node,
                                    visible=visible,
                                    admin=admin,
                                    read=read,
                                    write=write)
                                m2m_count += 1
                            else:
                                django_pks.append(modm_to_django[
                                    modm_m2m_value])
                        else:
                            # wth
                            print '\a'  # bells
                            print '\a'
                            print '\a'
                            print '\a'
                            print '\a'
                            print '\a'
                            print '\a'
                            import bpdb
                            bpdb.set_trace()

                    if len(django_pks) > 0:
                        attr.add(*django_pks)
                    m2m_count += len(django_pks)
                node_count += 1
                if node_count % page_size == 0 or node_count == total:
                    print 'Through {} nodes and {} m2m'.format(node_count,
                                                               m2m_count)
    print 'Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds())


def set_node_many_to_many_on_users(page_size=5000):
    print 'Starting {}...'.format(sys._getframe().f_code.co_name)
    user_count = 0
    m2m_count = 0
    start = datetime.now()
    total = MODMUser.find(build_query(m2m_node_fields, MODMUser)).count()
    print '{} Users'.format(total)
    while user_count < total:
        with transaction.atomic():
            for modm_user in MODMUser.find(build_query(
                    m2m_node_fields, MODMUser)).sort('-date_registered')[
                        user_count:page_size + user_count]:
                django_user = User.objects.get(
                    pk=modm_to_django[modm_user._id])
                for m2m_node_field in m2m_node_fields:
                    try:
                        attr = getattr(django_user, m2m_node_field)
                    except AttributeError as ex:
                        # node field doesn't exist on user
                        pass
                    else:
                        # node field exists, do the stuff
                        django_pks = []
                        for modm_m2m_value in getattr(modm_user,
                                                      m2m_node_field, []):
                            if isinstance(modm_m2m_value, MODMNode):
                                django_pks.append(modm_to_django[
                                    modm_m2m_value._id])
                            elif isinstance(modm_m2m_value, basestring):
                                django_pks.append(modm_to_django[
                                    modm_m2m_value])
                            elif isinstance(modm_m2m_value, Pointer):
                                django_pks.append(modm_to_django[
                                    modm_m2m_value.node._id])
                            else:
                                # wth
                                print '\a'  # bells!
                                print '\a'
                                print '\a'
                                print '\a'
                                print '\a'
                                print '\a'
                                print '\a'
                                import bpdb
                                bpdb.set_trace()

                        if len(django_pks) > 0:
                            attr.add(*django_pks)
                        m2m_count += len(django_pks)
                user_count += 1
                if user_count % page_size == 0 or user_count == total:
                    print 'Through {} users and {} m2m'.format(user_count,
                                                               m2m_count)
    print 'Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds())


def set_user_many_to_many_on_users(page_size=5000):
    print 'Starting {}...'.format(sys._getframe().f_code.co_name)
    user_count = 0
    m2m_count = 0
    start = datetime.now()
    total = MODMUser.find(build_query(m2m_user_fields, MODMUser)).count()
    print '{} Users'.format(total)
    while user_count < total:
        with transaction.atomic():
            for modm_user in MODMUser.find(build_query(
                    m2m_user_fields, MODMUser)).sort('-date_registered')[
                        user_count:page_size + user_count]:
                django_user = User.objects.get(
                    pk=modm_to_django[modm_user._id])
                for m2m_user_field in m2m_user_fields:
                    try:
                        attr = getattr(django_user, m2m_user_field)
                    except AttributeError as ex:
                        # node field doesn't exist on user
                        pass
                    else:
                        # node field exists, do the stuff
                        django_pks = []
                        for modm_m2m_value in getattr(modm_user,
                                                      m2m_user_field, []):
                            if isinstance(modm_m2m_value, MODMUser):
                                django_pks.append(modm_to_django[
                                    modm_m2m_value._id])
                            elif isinstance(modm_m2m_value, basestring):
                                django_pks.append(modm_to_django[
                                    modm_m2m_value])
                            else:
                                # wth
                                print '\a'  # bells!
                                print '\a'
                                print '\a'
                                print '\a'
                                print '\a'
                                print '\a'
                                print '\a'
                                import bpdb

                                bpdb.set_trace()

                        if len(django_pks) > 0:
                            attr.add(*django_pks)
                        m2m_count += len(django_pks)
                user_count += 1
                if user_count % page_size == 0 or user_count == total:
                    print 'Through {} users and {} m2m'.format(user_count,
                                                               m2m_count)
    print 'Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds())


def set_system_tag_many_to_many_on_users(page_size=10000):
    print 'Starting {}...'.format(sys._getframe().f_code.co_name)
    user_count = 0
    m2m_count = 0
    start = datetime.now()
    total = MODMUser.find(build_query(m2m_tag_fields, MODMUser)).count()
    print '{} Users'.format(total)
    while user_count < total:
        with transaction.atomic():
            for modm_user in MODMUser.find(build_query(
                    m2m_tag_fields, MODMUser)).sort('-date_registered')[
                        user_count:page_size + user_count]:
                django_user = User.objects.get(
                    pk=modm_to_django[modm_user._id])
                for m2m_tag_field in m2m_tag_fields:
                    try:
                        attr = getattr(django_user, m2m_tag_field)
                    except AttributeError as ex:
                        # node field doesn't exist on user
                        pass
                    else:
                        # node field exists, do the stuff
                        django_pks = []
                        for modm_m2m_value in getattr(modm_user, m2m_tag_field,
                                                      []):
                            if isinstance(modm_m2m_value, MODMTag):
                                django_pks.append(modm_to_django[
                                    '{}:system'.format(modm_m2m_value)])
                            elif isinstance(modm_m2m_value, basestring):
                                django_pks.append(modm_to_django[
                                    '{}:system'.format(modm_m2m_value)])
                            else:
                                # wth
                                print '\a'  # bells!
                                print '\a'
                                print '\a'
                                print '\a'
                                print '\a'
                                print '\a'
                                print '\a'
                                import bpdb

                                bpdb.set_trace()

                        if len(django_pks) > 0:
                            attr.add(*django_pks)
                        m2m_count += len(django_pks)
                user_count += 1
                if user_count % page_size == 0 or user_count == total:
                    print 'Through {} users and {} m2m'.format(user_count,
                                                               m2m_count)
    print 'Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds())


def set_tag_many_to_many_on_nodes(page_size=10000):
    print 'Starting {}...'.format(sys._getframe().f_code.co_name)
    node_count = 0
    m2m_count = 0
    start = datetime.now()
    total = MODMNode.find(build_query(m2m_tag_fields, MODMNode)).count()
    print '{} Nodes'.format(total)
    while node_count < total:
        with transaction.atomic():
            for modm_node in MODMNode.find(build_query(
                    m2m_tag_fields, MODMNode)).sort('-date_modified')[
                        node_count:page_size + node_count]:
                django_node = Node.objects.get(
                    pk=modm_to_django[modm_node._id])
                for m2m_tag_field in m2m_tag_fields:
                    try:
                        attr = getattr(django_node, m2m_tag_field)
                    except AttributeError as ex:
                        # node field doesn't exist on node
                        pass
                    else:
                        # node field exists, do the stuff
                        django_pks = []
                        for modm_m2m_value in getattr(modm_node, m2m_tag_field,
                                                      []):
                            suffix = 'system' if m2m_tag_field == 'system_tags' else 'not_system'
                            if isinstance(modm_m2m_value, MODMTag):
                                django_pks.append(modm_to_django[
                                    '{}:{}'.format(modm_m2m_value._id,
                                                   suffix)])
                            elif isinstance(modm_m2m_value, basestring):
                                django_pks.append(modm_to_django[
                                    '{}:{}'.format(modm_m2m_value, suffix)])
                            elif modm_m2m_value is None:
                                print 'Tag of None found on Node {}'.format(
                                    modm_node._id)
                            else:
                                # wth
                                print '\a'  # bells!
                                print '\a'
                                print '\a'
                                print '\a'
                                print '\a'
                                print '\a'
                                print '\a'
                                import bpdb

                                bpdb.set_trace()

                        if len(django_pks) > 0:
                            attr.add(*django_pks)
                        m2m_count += len(django_pks)
                node_count += 1
                if node_count % page_size == 0 or node_count == total:
                    print 'Through {} nodes and {} m2m'.format(node_count,
                                                               m2m_count)
    print 'Done with {} in {} seconds...'.format(
        sys._getframe().f_code.co_name,
        (datetime.now() - start).total_seconds())


def build_pk_caches():
    # build a lookup table of all guids to pks
    modm_to_django = {x['_guid__guid']: x['pk']
                      for x in Node.objects.all().values('_guid__guid', 'pk')}
    modm_to_django.update({x['_guid__guid']: x['pk']
                           for x in User.objects.all().values('_guid__guid',
                                                              'pk')})
    modm_to_django.update({'{}:system'.format(x['_id']): x['pk']
                           for x in Tag.objects.filter(system=True).values(
                               '_id', 'pk')})
    modm_to_django.update({'{}:not_system'.format(x['_id']): x['pk']
                           for x in Tag.objects.filter(system=False).values(
                               '_id', 'pk')})
    return modm_to_django

# def main(dry=True):
# start = datetime.now()
# # save_bare_nodes()
# # save_bare_users()
# # save_bare_tags()
# # save_bare_system_tags()
# # global modm_to_django
# # if modm_to_django == {}:
# #     # build a lookup table of all guids to pks
# #     modm_to_django = {x['_guid__guid']: x['pk']
# #                           for x in Node.objects.all().values('_guid__guid',
# #                                                              'pk')}
# #     modm_to_django.update({x['_guid__guid']: x['pk']
# #                            for x in User.objects.all().values('_guid__guid',
# #                                                               'pk')})
#
# modm_to_django = build_pk_caches()
#
# print 'cached {} modm to django key mappings'.format(len(
#     modm_to_django.keys()))
#
# # set_node_foreign_keys_on_nodes()
# # set_user_foreign_keys_on_nodes()
# # set_user_foreign_keys_on_users()
# # set_node_many_to_many_on_nodes()
# # set_user_many_to_many_on_nodes()
# # set_node_many_to_many_on_users()
# # set_user_many_to_many_on_users()
# set_tag_many_to_many_on_users()
# print 'Finished in {} seconds...'.format((datetime.now() - start
#                                           ).total_seconds())
# # if dry:
# #     raise DryMigrationException()
global modm_to_django
modm_to_django = build_pk_caches()
print 'Cached {} MODM to django mappings...'.format(len(modm_to_django.keys()))

# -*- coding: utf-8 -*-
# pylint: disable=no-member
from __future__ import unicode_literals

import json

from django.http import JsonResponse
from django.db.utils import IntegrityError
from django.shortcuts import render
from django.contrib.auth.models import User

from users.models import Profile


def index(request):
    """Landing page"""
    return render(request, 'index.html', {'title': 'South Austin Bass Club'})


def register(request):
    """Allows users to register with the site

    :param str user_type: The user type
    :param str first_name: The user's first name
    :param srt last_name: The user's last name
    :param str phone: The user's phone number
    :param str username: The user's username (e-mail address)
    :param str password: The user's password

    """
    params = json.loads(request.body)
    base_user = None
    delete_user = True
    try:

        if (params['user_type'] not in [item[0] for item in Profile.TYPE_CHOICES]):
            return JsonResponse(
                {
                    'status': -1,
                    'error': 'user_type %s does not exist' % params['user_type']
                }
            )

        base_user = User.objects.create(
            username=params['username'],
            first_name=params['first_name'],
            last_name=params['last_name'],
            email=params['username']
        )
        base_user.set_password(params['password'])
        base_user.save()
        Profile.objects.create(
            user=base_user,
            phone_number=params['phone'],
            type=params['user_type']
        )
        delete_user = False

    except IntegrityError:
        return JsonResponse({'status': -1, 'error': 'User %s already exists' % params['username']})
    except KeyError as error:
        return JsonResponse(
            {
                'status': -1,
                'error': 'Parameter %s is required' % unicode(error).replace('"', '')
            }
        )
    finally:
        if (delete_user is True and base_user is not None):
            base_user.delete()

    return JsonResponse({'status': 0})

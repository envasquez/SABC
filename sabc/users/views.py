# -*- coding: utf-8 -*-
# pylint: disable=no-member
from __future__ import unicode_literals

import json

from django.shortcuts import render
from django.contrib.auth.forms import UserCreationForm

from users.models import Profile

posts = [
    {
        'name': 'Lake Travis Tournament 1 - Jan 27, 2019',
        'ramp': 'Tatum',
        'time_start': '7am',
        'time_end': '4pm'
    },
    {
        'name': 'Lake Richland Chambers 2019 Tournament 2 - Feb 23 & 24',
        'ramp': 'Cottonwood Shores',
        'time_start': '7am',
        'time_end': '3pm'
    }
]

def index(request):
    """Landing page"""
    return render(request, 'index.html', {'title': 'South Austin Bass Club', 'posts': posts})


def register(request):
    """Allows a user to register with the site"""
    form = UserCreationForm()

    return render(request, 'register.html', {'title': 'SABC Registration', 'form': form})






# def register(request):
#     """Allows users to register with the site

#     :param str user_type: The user type
#     :param str first_name: The user's first name
#     :param srt last_name: The user's last name
#     :param str phone: The user's phone number
#     :param str username: The user's username (e-mail address)
#     :param str password: The user's password

#     """
    # params = json.loads(request.body)
    # base_user = None
    # delete_user = True
    # try:

    #     if (params['user_type'] not in [item[0] for item in Profile.TYPE_CHOICES]):
    #         return JsonResponse(
    #             {
    #                 'status': -1,
    #                 'error': 'user_type %s does not exist' % params['user_type']
    #             }
    #         )

    #     base_user = User.objects.create(
    #         username=params['username'],
    #         first_name=params['first_name'],
    #         last_name=params['last_name'],
    #         email=params['username']
    #     )
    #     base_user.set_password(params['password'])
    #     base_user.save()
    #     Profile.objects.create(
    #         user=base_user,
    #         phone_number=params['phone'],
    #         type=params['user_type']
    #     )
    #     delete_user = False

    # except IntegrityError:
    #     return JsonResponse({'status': -1, 'error': 'User %s already exists' % params['username']})
    # except KeyError as error:
    #     return JsonResponse(
    #         {
    #             'status': -1,
    #             'error': 'Parameter %s is required' % unicode(error).replace('"', '')
    #         }
    #     )
    # finally:
    #     if (delete_user is True and base_user is not None):
    #         base_user.delete()

    # return JsonResponse({'status': 0})

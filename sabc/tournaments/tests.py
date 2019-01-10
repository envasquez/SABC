# -*- coding: utf-8 -*-
"""Tests for the user registration API"""
from __future__ import unicode_literals

import json
import random

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from huh.tests.base import HUHBase

from users.models import Profile


class UserRegistrationTest(HUHBase):
    """Tests for the user registration API"""

    def setUp(self):
        """Sets the required test parameters"""
        super(UserRegistrationTest, self).setUp()
        self.params = {
            'user_type': random.choice(['property-manager', 'builder', 'realtor']),
            'username': 'billy@huh.com',
            'password': 'password!!123',
            'last_name': 'Thorton',
            'first_name': 'Billy',
            'phone': '512-555-8652'
        }
        self.url = '/register'

    def test_register(self):
        """Verify that you can register a user"""
        self._verify_json_success(
            json.loads(
                self.client.post(
                    self.url,
                    json.dumps(self.params),
                    content_type='application/json'
                ).content
            )
        )
        #
        # Validate user creation
        #
        user = User.objects.get(username=self.params['username'])
        huh_user = HUHUser.objects.get(user=user)
        for key, value in self.params.items():
            if (key == 'password'):
                continue
            elif (key in ['phone', 'user_type']):
                if (key == 'user_type'):
                    key = 'type'
                else:
                    key = 'phone_number'
                self.assertEqual(value, getattr(huh_user, key))
            else:
                self.assertEqual(value, getattr(user, key))
        #
        # Validate the password
        #
        self.assertIsNotNone(
            authenticate(
                request=None,
                username=self.params['username'],
                password=self.params['password']
            )
        )

    def test_register_dup_username(self):
        """Verify that an error is raised if someone tries to register the same user twice"""
        # First registration
        self._verify_json_success(
            json.loads(
                self.client.post(
                    self.url,
                    json.dumps(self.params),
                    content_type='application/json'
                ).content
            )
        )

        # Second registration
        self._verify_json_failure(
            params=json.loads(
                self.client.post(
                    self.url,
                    json.dumps(self.params),
                    content_type='application/json'
                ).content
            ),
            expected_error='User %s already exists' % self.params['username']
        )

    def test_invalid_user_type(self):
        """Verify that invalid users types are rejected"""
        self.params['user_type'] = 'foo'

        self._verify_json_failure(
            params=json.loads(
                self.client.post(
                    self.url,
                    json.dumps(self.params),
                    content_type='application/json'
                ).content
            ),
            expected_error='user_type foo does not exist'
        )

    def test_required_field_first_name(self):
        """Verify that the API call fails if required fields are missing"""
        self._test_required_field('first_name')

    def test_required_field_last_name(self):
        """Verify that the API call fails if required fields are missing"""
        self._test_required_field('last_name')

    def test_required_field_username(self):
        """Verify that the API call fails if required fields are missing"""
        self._test_required_field('username')

    def test_required_field_phone(self):
        """Verify that the API call fails if required fields are missing"""
        self._test_required_field('phone')

    def test_required_field_user_type(self):
        """Verify that the API call fails if required fields are missing"""
        self._test_required_field('user_type')

    def test_no_orphaned_user(self):
        """Verify that if creating a HUHUser fails, no User is created"""
        del self.params['phone']
        self._verify_json_failure(
            params=json.loads(
                self.client.post(
                    self.url,
                    json.dumps(self.params),
                    content_type='application/json'
                ).content
            ),
            expected_error="Parameter u'phone' is required"
        )

        self.assertFalse(User.objects.filter(username=self.params['username']).exists())
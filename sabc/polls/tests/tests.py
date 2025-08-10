# -*- coding: utf-8 -*-
"""
Comprehensive test suite for the polls application.

Tests cover:
- Model behavior and validation
- View access control and functionality
- Form validation
- Poll voting logic and restrictions
- Staff-only poll creation
"""

import datetime
from unittest.mock import patch

import pytz
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from tournaments.models.lakes import Lake
from users.models import Angler, Officers

from polls.forms import LakePollForm
from polls.models import LakePoll, LakeVote

User = get_user_model()


class LakePollModelTests(TestCase):
    """Test LakePoll model functionality."""

    def setUp(self):
        self.lake1 = Lake.objects.create(name="Austin")
        self.lake2 = Lake.objects.create(name="Travis")

        # Create a poll for testing
        self.poll = LakePoll.objects.create(
            name="Test Poll",
            end_date=datetime.date.today() + datetime.timedelta(days=1),
            end_time=datetime.time(19, 0),  # 7 PM
        )
        self.poll.choices.add(self.lake1, self.lake2)

    def test_poll_str_representation(self):
        """Test poll string representation."""
        self.assertEqual(str(self.poll), "Test Poll")

    def test_poll_absolute_url(self):
        """Test poll get_absolute_url method."""
        self.assertEqual(self.poll.get_absolute_url(), reverse("polls"))

    def test_poll_is_active_future_end_date(self):
        """Test poll is active when end date is in the future."""
        future_poll = LakePoll.objects.create(
            name="Future Poll",
            end_date=datetime.date.today() + datetime.timedelta(days=5),
            end_time=datetime.time(19, 0),
        )
        self.assertTrue(future_poll.is_active())

    def test_poll_is_active_past_end_date(self):
        """Test poll is not active when end date is in the past."""
        past_poll = LakePoll.objects.create(
            name="Past Poll",
            end_date=datetime.date.today() - datetime.timedelta(days=1),
            end_time=datetime.time(19, 0),
        )
        self.assertFalse(past_poll.is_active())

    def test_poll_is_active_completed(self):
        """Test poll is not active when marked complete."""
        self.poll.complete = True
        self.poll.save()
        self.assertFalse(self.poll.is_active())

    def test_poll_is_active_no_end_date(self):
        """Test poll is not active when no end date is set."""
        no_date_poll = LakePoll.objects.create(name="No Date Poll")
        self.assertFalse(no_date_poll.is_active())

    @patch("datetime.datetime")
    def test_poll_is_active_same_day_before_end_time(self, mock_datetime):
        """Test poll is active on end date before end time."""
        today = datetime.date.today()
        end_time = datetime.time(19, 0)  # 7 PM
        current_time = datetime.datetime.combine(today, datetime.time(18, 0))  # 6 PM
        mock_datetime.now.return_value = pytz.timezone("US/Central").localize(
            current_time
        )
        mock_datetime.combine = datetime.datetime.combine
        mock_datetime.date = datetime.date

        same_day_poll = LakePoll.objects.create(
            name="Same Day Poll",
            end_date=today,
            end_time=end_time,
        )
        self.assertTrue(same_day_poll.is_active())

    @patch("datetime.datetime")
    def test_poll_is_active_same_day_after_end_time(self, mock_datetime):
        """Test poll is not active on end date after end time."""
        today = datetime.date.today()
        end_time = datetime.time(19, 0)  # 7 PM
        current_time = datetime.datetime.combine(today, datetime.time(20, 0))  # 8 PM
        mock_datetime.now.return_value = pytz.timezone("US/Central").localize(
            current_time
        )
        mock_datetime.combine = datetime.datetime.combine
        mock_datetime.date = datetime.date

        same_day_poll = LakePoll.objects.create(
            name="Same Day Poll",
            end_date=today,
            end_time=end_time,
        )
        self.assertFalse(same_day_poll.is_active())

    def test_poll_save_sets_default_end_time(self):
        """Test poll save sets default end time if not provided."""
        poll = LakePoll.objects.create(
            name="No Time Poll",
            end_date=datetime.date.today() + datetime.timedelta(days=1),
        )
        self.assertEqual(poll.end_time, datetime.time(19, 0))

    def test_poll_save_marks_complete_if_past_end_date(self):
        """Test poll save automatically marks complete if past end date."""
        past_poll = LakePoll.objects.create(
            name="Past Poll",
            end_date=datetime.date.today() - datetime.timedelta(days=1),
            end_time=datetime.time(19, 0),
        )
        self.assertTrue(past_poll.complete)


class LakeVoteModelTests(TestCase):
    """Test LakeVote model functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.angler = Angler.objects.create(
            user=self.user, phone_number="5125551234", member=True
        )

        self.lake = Lake.objects.create(name="Test Lake")
        self.poll = LakePoll.objects.create(
            name="Test Poll",
            end_date=datetime.date.today() + datetime.timedelta(days=1),
        )
        self.poll.choices.add(self.lake)

    def test_vote_creation(self):
        """Test creating a vote."""
        vote = LakeVote.objects.create(
            poll=self.poll, choice=self.lake, angler=self.angler
        )
        self.assertEqual(vote.poll, self.poll)
        self.assertEqual(vote.choice, self.lake)
        self.assertEqual(vote.angler, self.angler)

    def test_vote_str_representation(self):
        """Test vote string representation."""
        vote = LakeVote.objects.create(
            poll=self.poll, choice=self.lake, angler=self.angler
        )
        expected = f"{self.poll}: {self.lake} {self.angler}"
        self.assertEqual(str(vote), expected)

    def test_vote_timestamp_auto_set(self):
        """Test vote timestamp is automatically set."""
        vote = LakeVote.objects.create(
            poll=self.poll, choice=self.lake, angler=self.angler
        )
        self.assertIsNotNone(vote.timestamp)


class LakePollFormTests(TestCase):
    """Test LakePollForm functionality."""

    def setUp(self):
        self.lake1 = Lake.objects.create(name="Lake 1")
        self.lake2 = Lake.objects.create(name="Lake 2")

    def test_form_valid_data(self):
        """Test form with valid data."""
        form_data = {
            "name": "Test Poll",
            "choices": [self.lake1.id, self.lake2.id],
            "end_date": datetime.date.today() + datetime.timedelta(days=7),
            "end_time": datetime.time(19, 0),
            "description": "Test poll description",
        }
        form = LakePollForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_missing_name(self):
        """Test form validation fails with missing name."""
        form_data = {
            "choices": [self.lake1.id],
            "end_date": datetime.date.today() + datetime.timedelta(days=7),
        }
        form = LakePollForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_form_no_choices(self):
        """Test form allows no choices (can be set later)."""
        form_data = {
            "name": "Test Poll",
            "end_date": datetime.date.today() + datetime.timedelta(days=7),
        }
        form = LakePollForm(data=form_data)
        self.assertTrue(form.is_valid())


class LakePollViewTests(TestCase):
    """Test poll views and access control."""

    def setUp(self):
        self.client = Client()

        # Create users with different permissions
        self.member_user = User.objects.create_user(
            username="member", email="member@test.com", password="testpass123"
        )
        self.member_angler = Angler.objects.create(
            user=self.member_user, phone_number="5125551234", member=True
        )

        self.guest_user = User.objects.create_user(
            username="guest", email="guest@test.com", password="testpass123"
        )
        self.guest_angler = Angler.objects.create(
            user=self.guest_user, phone_number="5125551235", member=False
        )

        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@test.com",
            password="testpass123",
            is_staff=True,
        )
        self.staff_angler = Angler.objects.create(
            user=self.staff_user, phone_number="5125551236", member=True
        )

        # Create test lakes and polls
        self.lake1 = Lake.objects.create(name="Test Lake 1")
        self.lake2 = Lake.objects.create(name="Test Lake 2")

        self.poll = LakePoll.objects.create(
            name="Test Poll",
            end_date=datetime.date.today() + datetime.timedelta(days=7),
        )
        self.poll.choices.add(self.lake1, self.lake2)

    def test_polls_list_requires_membership(self):
        """Test polls list requires membership."""
        # Anonymous user
        response = self.client.get(reverse("polls"))
        self.assertIn(
            response.status_code, [302, 403]
        )  # Redirect to login or forbidden

        # Guest user (no membership)
        self.client.login(username="guest", password="testpass123")
        response = self.client.get(reverse("polls"))
        self.assertEqual(response.status_code, 403)

        # Member user
        self.client.login(username="member", password="testpass123")
        response = self.client.get(reverse("polls"))
        self.assertEqual(response.status_code, 200)

    def test_polls_list_displays_polls(self):
        """Test polls list displays polls correctly."""
        self.client.login(username="member", password="testpass123")
        response = self.client.get(reverse("polls"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Poll")
        self.assertIn("polls", response.context)

    def test_poll_create_requires_staff(self):
        """Test poll creation requires staff permissions."""
        # Anonymous user
        response = self.client.get(reverse("lakepoll-create"))
        self.assertIn(response.status_code, [302, 403])

        # Member user (not staff)
        self.client.login(username="member", password="testpass123")
        response = self.client.get(reverse("lakepoll-create"))
        self.assertEqual(response.status_code, 403)

        # Staff user
        self.client.login(username="staff", password="testpass123")
        response = self.client.get(reverse("lakepoll-create"))
        self.assertEqual(response.status_code, 200)

    def test_poll_create_form_rendering(self):
        """Test poll creation form renders correctly."""
        self.client.login(username="staff", password="testpass123")
        response = self.client.get(reverse("lakepoll-create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "name")
        self.assertContains(response, "choices")
        self.assertContains(response, "end_date")

    def test_poll_create_post_valid_data(self):
        """Test creating poll with valid data."""
        self.client.login(username="staff", password="testpass123")

        form_data = {
            "name": "New Test Poll",
            "choices": [self.lake1.id, self.lake2.id],
            "end_date": (datetime.date.today() + datetime.timedelta(days=14)).strftime(
                "%Y-%m-%d"
            ),
            "end_time": "19:00:00",
            "description": "New poll description",
        }

        response = self.client.post(reverse("lakepoll-create"), form_data)
        self.assertIn(response.status_code, [301, 302])  # Redirect on success

        # Verify poll was created
        new_poll = LakePoll.objects.filter(name="New Test Poll").first()
        self.assertIsNotNone(new_poll)
        self.assertEqual(new_poll.choices.count(), 2)

    def test_poll_detail_view_member_access(self):
        """Test poll detail view access for members."""
        self.client.login(username="member", password="testpass123")
        response = self.client.get(reverse("poll", kwargs={"pid": self.poll.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Poll")

    def test_poll_detail_view_guest_denied(self):
        """Test poll detail view denies guest access."""
        self.client.login(username="guest", password="testpass123")
        response = self.client.get(reverse("poll", kwargs={"pid": self.poll.id}))
        self.assertEqual(response.status_code, 403)


class PollVotingTests(TestCase):
    """Test poll voting functionality."""

    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(
            username="member", email="member@test.com", password="testpass123"
        )
        self.angler = Angler.objects.create(
            user=self.user, phone_number="5125551234", member=True
        )

        self.lake1 = Lake.objects.create(name="Lake 1")
        self.lake2 = Lake.objects.create(name="Lake 2")

        self.active_poll = LakePoll.objects.create(
            name="Active Poll",
            end_date=datetime.date.today() + datetime.timedelta(days=7),
        )
        self.active_poll.choices.add(self.lake1, self.lake2)

        self.closed_poll = LakePoll.objects.create(
            name="Closed Poll",
            end_date=datetime.date.today() - datetime.timedelta(days=1),
            complete=True,
        )
        self.closed_poll.choices.add(self.lake1, self.lake2)

    def test_vote_on_active_poll(self):
        """Test voting on an active poll."""
        self.client.login(username="member", password="testpass123")

        response = self.client.post(
            reverse("poll", kwargs={"pid": self.active_poll.id}),
            {"choice": self.lake1.id},
        )

        # Should redirect after successful vote
        self.assertIn(response.status_code, [301, 302])

        # Verify vote was recorded
        vote = LakeVote.objects.filter(
            poll=self.active_poll, angler=self.angler, choice=self.lake1
        ).first()
        self.assertIsNotNone(vote)

    def test_cannot_vote_twice(self):
        """Test user cannot vote twice on same poll."""
        # Create initial vote
        LakeVote.objects.create(
            poll=self.active_poll, choice=self.lake1, angler=self.angler
        )

        self.client.login(username="member", password="testpass123")

        response = self.client.post(
            reverse("poll", kwargs={"pid": self.active_poll.id}),
            {"choice": self.lake2.id},
        )

        # Should still be on poll page with error message
        if response.status_code == 200:
            # Check for error message in context or content
            pass

        # Verify only original vote exists
        votes = LakeVote.objects.filter(poll=self.active_poll, angler=self.angler)
        self.assertEqual(votes.count(), 1)
        self.assertEqual(votes.first().choice, self.lake1)

    def test_cannot_vote_on_closed_poll(self):
        """Test user cannot vote on closed poll."""
        self.client.login(username="member", password="testpass123")

        response = self.client.post(
            reverse("poll", kwargs={"pid": self.closed_poll.id}),
            {"choice": self.lake1.id},
        )

        # Should show error or redirect
        if response.status_code == 200:
            # Poll should be marked as closed
            pass

        # Verify no vote was recorded
        vote_count = LakeVote.objects.filter(
            poll=self.closed_poll, angler=self.angler
        ).count()
        self.assertEqual(vote_count, 0)

    def test_voting_requires_authentication(self):
        """Test voting requires authentication."""
        response = self.client.post(
            reverse("poll", kwargs={"pid": self.active_poll.id}),
            {"choice": self.lake1.id},
        )

        # Should redirect to login or be forbidden
        self.assertIn(response.status_code, [302, 403])

        # Verify no vote was recorded
        vote_count = LakeVote.objects.filter(poll=self.active_poll).count()
        self.assertEqual(vote_count, 0)

    def test_voting_displays_results(self):
        """Test poll view displays voting results."""
        # Create some votes
        other_user = User.objects.create_user(
            username="other", email="other@test.com", password="testpass123"
        )
        other_angler = Angler.objects.create(
            user=other_user, phone_number="5125551237", member=True
        )

        LakeVote.objects.create(
            poll=self.active_poll, choice=self.lake1, angler=self.angler
        )
        LakeVote.objects.create(
            poll=self.active_poll, choice=self.lake1, angler=other_angler
        )

        self.client.login(username="member", password="testpass123")
        response = self.client.get(reverse("poll", kwargs={"pid": self.active_poll.id}))

        self.assertEqual(response.status_code, 200)
        # Should display vote counts
        self.assertContains(response, "Lake 1")
        self.assertContains(response, "2")  # Vote count

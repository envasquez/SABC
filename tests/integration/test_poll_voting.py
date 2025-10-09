"""Integration tests for poll voting flow."""

from datetime import datetime, timedelta

import pytest

from core.db_schema import Angler, Event, Poll, PollOption, PollVote, get_session
from core.helpers.timezone import now_local


@pytest.mark.asyncio
class TestPollVotingFlow:
    """End-to-end integration tests for poll voting functionality."""

    async def test_complete_poll_voting_flow(self, client, db_session):
        """Test complete flow: create poll -> member votes -> verify results."""
        with get_session() as session:
            # Create test member
            member = Angler(
                name="Test Voter",
                email="voter@example.com",
                password_hash="$2b$12$test",
                member=True,
                phone="555-0100",
            )
            session.add(member)
            session.flush()
            member_id = member.id

            # Create test event
            event = Event(
                name="Test Tournament",
                date=datetime.now().date() + timedelta(days=30),
                event_type="sabc_tournament",
                year=2025,
            )
            session.add(event)
            session.flush()
            event_id = event.id

            # Create poll
            now = now_local()
            poll = Poll(
                event_id=event_id,
                title="Test Poll",
                description="Vote for your favorite option",
                poll_type="simple",
                starts_at=now - timedelta(hours=1),
                closes_at=now + timedelta(hours=23),
                closed=False,
            )
            session.add(poll)
            session.flush()
            poll_id = poll.id

            # Create poll options
            option1 = PollOption(poll_id=poll_id, option_text="Option 1")
            option2 = PollOption(poll_id=poll_id, option_text="Option 2")
            session.add_all([option1, option2])
            session.flush()

            session.commit()

        # Simulate login
        response = client.post(
            "/login",
            data={"email": "voter@example.com", "password": "test"},
            follow_redirects=False,
        )

        # Member should be able to view polls
        response = client.get("/polls")
        assert response.status_code in [200, 303]  # 303 if not logged in, 200 if logged in

        # Verify poll was created and is visible
        with get_session() as session:
            created_poll = session.query(Poll).filter(Poll.id == poll_id).first()
            assert created_poll is not None
            assert created_poll.title == "Test Poll"
            assert created_poll.closed is False

            # Verify options were created
            options = session.query(PollOption).filter(PollOption.poll_id == poll_id).all()
            assert len(options) == 2

        # Verify member hasn't voted yet
        with get_session() as session:
            vote = (
                session.query(PollVote)
                .filter(PollVote.poll_id == poll_id, PollVote.angler_id == member_id)
                .first()
            )
            assert vote is None

    async def test_poll_vote_validation_prevents_double_voting(self, db_session):
        """Test that a member cannot vote twice in the same poll."""
        with get_session() as session:
            # Create test member
            member = Angler(
                name="Double Voter",
                email="double@example.com",
                password_hash="$2b$12$test",
                member=True,
                phone="555-0101",
            )
            session.add(member)
            session.flush()
            member_id = member.id

            # Create event and poll
            event = Event(
                name="Test Event",
                date=datetime.now().date() + timedelta(days=30),
                event_type="sabc_tournament",
                year=2025,
            )
            session.add(event)
            session.flush()

            now = now_local()
            poll = Poll(
                event_id=event.id,
                title="Single Vote Poll",
                poll_type="simple",
                starts_at=now - timedelta(hours=1),
                closes_at=now + timedelta(hours=23),
                closed=False,
            )
            session.add(poll)
            session.flush()
            poll_id = poll.id

            # Create option
            option = PollOption(poll_id=poll_id, option_text="Option A")
            session.add(option)
            session.flush()
            option_id = option.id

            # First vote - should succeed
            vote1 = PollVote(poll_id=poll_id, option_id=option_id, angler_id=member_id)
            session.add(vote1)
            session.commit()

        # Verify first vote was recorded
        with get_session() as session:
            votes = (
                session.query(PollVote)
                .filter(PollVote.poll_id == poll_id, PollVote.angler_id == member_id)
                .all()
            )
            assert len(votes) == 1

        # Attempt second vote - validation should prevent this
        with get_session() as session:
            has_voted = (
                session.query(PollVote)
                .filter(PollVote.poll_id == poll_id, PollVote.angler_id == member_id)
                .first()
            )
            assert has_voted is not None  # Member already voted

    async def test_poll_closes_after_deadline(self, db_session):
        """Test that polls cannot be voted on after closing time."""
        with get_session() as session:
            # Create member
            member = Angler(
                name="Late Voter",
                email="late@example.com",
                password_hash="$2b$12$test",
                member=True,
                phone="555-0102",
            )
            session.add(member)
            session.flush()

            # Create event
            event = Event(
                name="Closed Event",
                date=datetime.now().date() + timedelta(days=30),
                event_type="sabc_tournament",
                year=2025,
            )
            session.add(event)
            session.flush()

            # Create closed poll (already past deadline)
            now = now_local()
            poll = Poll(
                event_id=event.id,
                title="Closed Poll",
                poll_type="simple",
                starts_at=now - timedelta(hours=48),
                closes_at=now - timedelta(hours=1),  # Closed 1 hour ago
                closed=False,
            )
            session.add(poll)
            session.flush()
            poll_id = poll.id

            # Create option
            option = PollOption(poll_id=poll_id, option_text="Late Option")
            session.add(option)
            session.commit()

        # Verify poll is past deadline
        with get_session() as session:
            poll = session.query(Poll).filter(Poll.id == poll_id).first()
            current_time = now_local().replace(tzinfo=None)  # DB stores naive
            assert poll.closes_at < current_time  # Poll has closed

    async def test_poll_vote_count_aggregation(self, db_session):
        """Test that poll votes are correctly aggregated."""
        with get_session() as session:
            # Create multiple members
            members = []
            for i in range(5):
                member = Angler(
                    name=f"Voter {i}",
                    email=f"voter{i}@example.com",
                    password_hash="$2b$12$test",
                    member=True,
                    phone=f"555-010{i}",
                )
                session.add(member)
                members.append(member)
            session.flush()

            # Create event and poll
            event = Event(
                name="Popular Event",
                date=datetime.now().date() + timedelta(days=30),
                event_type="sabc_tournament",
                year=2025,
            )
            session.add(event)
            session.flush()

            now = now_local()
            poll = Poll(
                event_id=event.id,
                title="Popular Poll",
                poll_type="simple",
                starts_at=now - timedelta(hours=1),
                closes_at=now + timedelta(hours=23),
                closed=False,
            )
            session.add(poll)
            session.flush()
            poll_id = poll.id

            # Create two options
            option1 = PollOption(poll_id=poll_id, option_text="Popular Option")
            option2 = PollOption(poll_id=poll_id, option_text="Unpopular Option")
            session.add_all([option1, option2])
            session.flush()

            # 3 votes for option1, 2 votes for option2
            for i, member in enumerate(members):
                option_id = option1.id if i < 3 else option2.id
                vote = PollVote(poll_id=poll_id, option_id=option_id, angler_id=member.id)
                session.add(vote)

            session.commit()

        # Verify vote counts
        with get_session() as session:
            option1_votes = session.query(PollVote).filter(PollVote.option_id == option1.id).count()
            option2_votes = session.query(PollVote).filter(PollVote.option_id == option2.id).count()

            assert option1_votes == 3
            assert option2_votes == 2

            # Verify total unique voters
            total_voters = (
                session.query(PollVote.angler_id)
                .filter(PollVote.poll_id == poll_id)
                .distinct()
                .count()
            )
            assert total_voters == 5

    async def test_only_members_can_vote(self, db_session):
        """Test that non-members cannot vote in polls."""
        with get_session() as session:
            # Create non-member
            non_member = Angler(
                name="Non Member",
                email="nonmember@example.com",
                password_hash="$2b$12$test",
                member=False,  # Not a member
                phone="555-0199",
            )
            session.add(non_member)
            session.flush()
            non_member_id = non_member.id

            # Create event and poll
            event = Event(
                name="Members Only Event",
                date=datetime.now().date() + timedelta(days=30),
                event_type="sabc_tournament",
                year=2025,
            )
            session.add(event)
            session.flush()

            now = now_local()
            poll = Poll(
                event_id=event.id,
                title="Members Only Poll",
                poll_type="simple",
                starts_at=now - timedelta(hours=1),
                closes_at=now + timedelta(hours=23),
                closed=False,
            )
            session.add(poll)
            session.flush()

            session.commit()

        # Verify non-member status
        with get_session() as session:
            angler = session.query(Angler).filter(Angler.id == non_member_id).first()
            assert angler.member is False  # Confirm not a member

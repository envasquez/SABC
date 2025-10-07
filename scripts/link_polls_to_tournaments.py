#!/usr/bin/env python3
"""Link polls to tournaments based on matching event_id."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db_schema import Poll, Tournament, get_session


def link_polls_to_tournaments() -> None:
    """Link polls to tournaments where event_id matches."""
    with get_session() as session:
        # Get all tournaments without polls
        tournaments = (
            session.query(Tournament)
            .filter(Tournament.poll_id.is_(None), Tournament.event_id.isnot(None))
            .all()
        )

        print(f"Found {len(tournaments)} tournaments without polls")

        for tournament in tournaments:
            # Find poll with matching event_id
            poll = session.query(Poll).filter(Poll.event_id == tournament.event_id).first()

            if poll:
                print(
                    f"Linking tournament {tournament.id} (event {tournament.event_id}) to poll {poll.id}"
                )
                tournament.poll_id = poll.id
            else:
                print(f"No poll found for tournament {tournament.id} (event {tournament.event_id})")

        session.commit()
        print("Done linking polls to tournaments")


if __name__ == "__main__":
    link_polls_to_tournaments()

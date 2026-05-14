"""Read-only audit of SABC database integrity violations (no schema/data changes)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Any, List, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Row
from sqlalchemy.orm import Session

from core.db_schema import engine, get_session


def _fetch_all(session: Session, sql: str, **params: Any) -> List[Row[Any]]:
    """Execute a parameterized read-only query and return all rows."""
    return list(session.execute(text(sql), params).all())


def _scalar(session: Session, sql: str, **params: Any) -> int:
    """Execute a scalar-returning count query and return the int (0 if NULL)."""
    value = session.execute(text(sql), params).scalar()
    return int(value) if value is not None else 0


def check_duplicate_emails(session: Session) -> Tuple[int, List[Row[Any]], int]:
    """Find anglers sharing an email and count anglers with NULL email.

    Returns (duplicate_email_count, sample_rows, null_email_count).
    duplicate_email_count is the number of distinct emails appearing >1 time.
    """
    rows = _fetch_all(
        session,
        """
        SELECT email, COUNT(*) AS cnt
        FROM anglers
        WHERE email IS NOT NULL
        GROUP BY email
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT 10
        """,
    )
    dup_count = _scalar(
        session,
        """
        SELECT COUNT(*) FROM (
            SELECT email FROM anglers
            WHERE email IS NOT NULL
            GROUP BY email
            HAVING COUNT(*) > 1
        ) sub
        """,
    )
    null_count = _scalar(session, "SELECT COUNT(*) FROM anglers WHERE email IS NULL")
    return dup_count, rows, null_count


def check_poll_votes_null_fks(
    session: Session,
) -> Tuple[int, int, int, List[Row[Any]], List[Row[Any]], List[Row[Any]]]:
    """Count NULL FK rows in poll_votes for poll_id / angler_id / option_id."""
    poll_null = _scalar(session, "SELECT COUNT(*) FROM poll_votes WHERE poll_id IS NULL")
    angler_null = _scalar(session, "SELECT COUNT(*) FROM poll_votes WHERE angler_id IS NULL")
    option_null = _scalar(session, "SELECT COUNT(*) FROM poll_votes WHERE option_id IS NULL")

    sample_poll = (
        _fetch_all(
            session,
            "SELECT id, poll_id, angler_id, option_id, voted_at FROM poll_votes "
            "WHERE poll_id IS NULL ORDER BY id LIMIT 5",
        )
        if poll_null
        else []
    )
    sample_angler = (
        _fetch_all(
            session,
            "SELECT id, poll_id, angler_id, option_id, voted_at FROM poll_votes "
            "WHERE angler_id IS NULL ORDER BY id LIMIT 5",
        )
        if angler_null
        else []
    )
    sample_option = (
        _fetch_all(
            session,
            "SELECT id, poll_id, angler_id, option_id, voted_at FROM poll_votes "
            "WHERE option_id IS NULL ORDER BY id LIMIT 5",
        )
        if option_null
        else []
    )
    return poll_null, angler_null, option_null, sample_poll, sample_angler, sample_option


def check_results_null_fks(
    session: Session,
) -> Tuple[int, int, List[Row[Any]], List[Row[Any]]]:
    """Count NULL FK rows in results for tournament_id / angler_id."""
    tournament_null = _scalar(session, "SELECT COUNT(*) FROM results WHERE tournament_id IS NULL")
    angler_null = _scalar(session, "SELECT COUNT(*) FROM results WHERE angler_id IS NULL")

    sample_tournament = (
        _fetch_all(
            session,
            "SELECT id, tournament_id, angler_id, total_weight, place_finish FROM results "
            "WHERE tournament_id IS NULL ORDER BY id LIMIT 5",
        )
        if tournament_null
        else []
    )
    sample_angler = (
        _fetch_all(
            session,
            "SELECT id, tournament_id, angler_id, total_weight, place_finish FROM results "
            "WHERE angler_id IS NULL ORDER BY id LIMIT 5",
        )
        if angler_null
        else []
    )
    return tournament_null, angler_null, sample_tournament, sample_angler


def check_team_results_null_fks(
    session: Session,
) -> Tuple[int, int, List[Row[Any]], List[Row[Any]]]:
    """Count NULL FK rows in team_results for tournament_id / angler1_id.

    angler2_id is intentionally not checked: solo entries legitimately store
    NULL there.
    """
    tournament_null = _scalar(
        session, "SELECT COUNT(*) FROM team_results WHERE tournament_id IS NULL"
    )
    angler1_null = _scalar(session, "SELECT COUNT(*) FROM team_results WHERE angler1_id IS NULL")

    sample_tournament = (
        _fetch_all(
            session,
            "SELECT id, tournament_id, angler1_id, angler2_id, total_weight FROM team_results "
            "WHERE tournament_id IS NULL ORDER BY id LIMIT 5",
        )
        if tournament_null
        else []
    )
    sample_angler1 = (
        _fetch_all(
            session,
            "SELECT id, tournament_id, angler1_id, angler2_id, total_weight FROM team_results "
            "WHERE angler1_id IS NULL ORDER BY id LIMIT 5",
        )
        if angler1_null
        else []
    )
    return tournament_null, angler1_null, sample_tournament, sample_angler1


def check_duplicate_officer_positions(session: Session) -> Tuple[int, List[Row[Any]]]:
    """Find (position, year) pairs appearing more than once in officer_positions."""
    rows = _fetch_all(
        session,
        """
        SELECT position, year, COUNT(*) AS cnt
        FROM officer_positions
        GROUP BY position, year
        HAVING COUNT(*) > 1
        ORDER BY year DESC, position
        LIMIT 10
        """,
    )
    total = _scalar(
        session,
        """
        SELECT COUNT(*) FROM (
            SELECT position, year FROM officer_positions
            GROUP BY position, year
            HAVING COUNT(*) > 1
        ) sub
        """,
    )
    return total, rows


def check_poll_vote_null_angler_dupes(session: Session) -> Tuple[int, List[Row[Any]]]:
    """Find polls where multiple votes share angler_id IS NULL.

    The uq_poll_vote_angler(poll_id, angler_id) constraint is bypassed when
    angler_id is NULL because NULL != NULL in Postgres. Each such poll is
    suspicious: it indicates duplicate votes hidden behind NULLs.
    """
    rows = _fetch_all(
        session,
        """
        SELECT poll_id, COUNT(*) AS cnt
        FROM poll_votes
        WHERE angler_id IS NULL
        GROUP BY poll_id
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT 10
        """,
    )
    total = _scalar(
        session,
        """
        SELECT COUNT(*) FROM (
            SELECT poll_id FROM poll_votes
            WHERE angler_id IS NULL
            GROUP BY poll_id
            HAVING COUNT(*) > 1
        ) sub
        """,
    )
    return total, rows


def _format_rows(rows: List[Row[Any]], indent: str = "    ") -> str:
    """Render a list of Row objects as indented key=value lines."""
    if not rows:
        return f"{indent}(none)"
    lines: List[str] = []
    for row in rows:
        mapping = row._mapping
        fields = ", ".join(f"{k}={mapping[k]!r}" for k in mapping.keys())
        lines.append(f"{indent}{fields}")
    return "\n".join(lines)


def _database_label() -> str:
    """Return a human-readable label for the connected database (no creds)."""
    url = engine.url
    db = url.database or "<unknown>"
    host = url.host or "<local>"
    return f"{db} @ {host}"


def main() -> int:
    """Run all integrity checks and print a report. Exit 1 if any violations."""
    print("=== SABC DB Integrity Audit ===")
    print(f"Date: {datetime.now(timezone.utc).isoformat()}")
    print(f"Connected to: {_database_label()}")
    print()

    total_violations = 0

    with get_session() as session:
        # [1] Duplicate emails in anglers
        dup_email_count, dup_email_rows, null_email_count = check_duplicate_emails(session)
        total_violations += dup_email_count
        print("[1] Duplicate emails in anglers")
        print(f"  Violations: {dup_email_count}")
        if dup_email_rows:
            print("  Sample:")
            for row in dup_email_rows:
                print(f"    {row._mapping['email']}: {row._mapping['cnt']}")
        print()

        # [2] anglers.email NULL
        print("[2] anglers.email NULL")
        print(f"  Count: {null_email_count}")
        print("  (Informational only; email NULL is allowed by current schema.)")
        print()

        # [3] poll_votes NULL FKs
        (
            pv_poll_null,
            pv_angler_null,
            pv_option_null,
            pv_sample_poll,
            pv_sample_angler,
            pv_sample_option,
        ) = check_poll_votes_null_fks(session)
        pv_total = pv_poll_null + pv_angler_null + pv_option_null
        total_violations += pv_total
        print("[3] poll_votes NULL FKs")
        print(f"  poll_id NULL:   {pv_poll_null}")
        print(f"  angler_id NULL: {pv_angler_null}")
        print(f"  option_id NULL: {pv_option_null}")
        if pv_sample_poll:
            print("  Sample (poll_id NULL):")
            print(_format_rows(pv_sample_poll))
        if pv_sample_angler:
            print("  Sample (angler_id NULL):")
            print(_format_rows(pv_sample_angler))
        if pv_sample_option:
            print("  Sample (option_id NULL):")
            print(_format_rows(pv_sample_option))
        print()

        # [4] results NULL FKs
        r_tournament_null, r_angler_null, r_sample_t, r_sample_a = check_results_null_fks(session)
        r_total = r_tournament_null + r_angler_null
        total_violations += r_total
        print("[4] results NULL FKs")
        print(f"  tournament_id NULL: {r_tournament_null}")
        print(f"  angler_id NULL:     {r_angler_null}")
        if r_sample_t:
            print("  Sample (tournament_id NULL):")
            print(_format_rows(r_sample_t))
        if r_sample_a:
            print("  Sample (angler_id NULL):")
            print(_format_rows(r_sample_a))
        print()

        # [5] team_results NULL FKs (excluding legitimate angler2_id NULLs)
        tr_tournament_null, tr_angler1_null, tr_sample_t, tr_sample_a = check_team_results_null_fks(
            session
        )
        tr_total = tr_tournament_null + tr_angler1_null
        total_violations += tr_total
        print("[5] team_results NULL FKs (excluding legitimate angler2_id NULLs)")
        print(f"  tournament_id NULL: {tr_tournament_null}")
        print(f"  angler1_id NULL:    {tr_angler1_null}")
        if tr_sample_t:
            print("  Sample (tournament_id NULL):")
            print(_format_rows(tr_sample_t))
        if tr_sample_a:
            print("  Sample (angler1_id NULL):")
            print(_format_rows(tr_sample_a))
        print()

        # [6] officer_positions duplicate (position, year)
        op_total, op_rows = check_duplicate_officer_positions(session)
        total_violations += op_total
        print("[6] officer_positions duplicate (position, year)")
        print(f"  Violations: {op_total}")
        if op_rows:
            print("  Sample:")
            for row in op_rows:
                m = row._mapping
                print(f"    position={m['position']!r} year={m['year']}: {m['cnt']}")
        print()

        # [7] poll_votes uniqueness bypass via NULL angler_id
        bypass_total, bypass_rows = check_poll_vote_null_angler_dupes(session)
        total_violations += bypass_total
        print("[7] poll_votes uniqueness bypass via NULL angler_id")
        print(f"  Suspicious polls: {bypass_total}")
        if bypass_rows:
            print("  Sample:")
            for row in bypass_rows:
                m = row._mapping
                print(f"    poll_id={m['poll_id']}: {m['cnt']} votes with angler_id NULL")
        print()

    exit_code = 1 if total_violations > 0 else 0
    print("=== Summary ===")
    print("Total checks: 7")
    print(f"Violations found: {total_violations}")
    print(f"Exit code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

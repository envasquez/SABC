import os

from sqlalchemy import create_engine, text

# Support environment variable for database path
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///sabc.db")
engine = create_engine(DATABASE_URL, echo=False)

# Table definitions for database schema
TABLE_DEFINITIONS = [
    """anglers(
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        member BOOLEAN DEFAULT 1,
        is_admin BOOLEAN DEFAULT 0,
        active BOOLEAN DEFAULT 1,
        password_hash TEXT,
        year_joined INTEGER,
        phone TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """events(
        id INTEGER PRIMARY KEY,
        date DATE NOT NULL UNIQUE,
        year INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        event_type TEXT DEFAULT 'sabc_tournament' CHECK (event_type IN ('sabc_tournament', 'federal_holiday', 'other_tournament', 'club_event')),
        start_time TIME,
        weigh_in_time TIME,
        lake_name TEXT,
        ramp_name TEXT,
        entry_fee DECIMAL DEFAULT 25.00,
        is_cancelled BOOLEAN DEFAULT 0,
        holiday_name TEXT
    )""",
    """polls(
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        poll_type TEXT NOT NULL,
        event_id INTEGER,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        starts_at TIMESTAMP NOT NULL,
        closes_at TIMESTAMP NOT NULL,
        closed BOOLEAN DEFAULT 0,
        multiple_votes BOOLEAN DEFAULT 0,
        winning_option_id INTEGER
    )""",
    """poll_options(
        id INTEGER PRIMARY KEY,
        poll_id INTEGER,
        option_text TEXT NOT NULL,
        option_data TEXT,
        display_order INTEGER DEFAULT 0
    )""",
    """poll_votes(
        id INTEGER PRIMARY KEY,
        poll_id INTEGER,
        option_id INTEGER,
        angler_id INTEGER,
        voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(poll_id, option_id, angler_id)
    )""",
    """tournaments(
        id INTEGER PRIMARY KEY,
        event_id INTEGER,
        poll_id INTEGER,
        name TEXT NOT NULL,
        lake_name TEXT,
        ramp_name TEXT,
        start_time TIME,
        end_time TIME,
        fish_limit INTEGER DEFAULT 5,
        entry_fee DECIMAL DEFAULT 25.00,
        is_team BOOLEAN DEFAULT 1,
        is_paper BOOLEAN DEFAULT 0,
        big_bass_carryover DECIMAL DEFAULT 0.0,
        complete BOOLEAN DEFAULT 0,
        created_by INTEGER,
        limit_type TEXT DEFAULT 'angler'
    )""",
    """results(
        id INTEGER PRIMARY KEY,
        tournament_id INTEGER,
        angler_id INTEGER,
        num_fish INTEGER DEFAULT 0,
        total_weight DECIMAL DEFAULT 0.0,
        big_bass_weight DECIMAL DEFAULT 0.0,
        dead_fish_penalty DECIMAL DEFAULT 0.0,
        disqualified BOOLEAN DEFAULT 0,
        buy_in BOOLEAN DEFAULT 0,
        place_finish INTEGER,
        points INTEGER DEFAULT 0
    )""",
    """team_results(
        id INTEGER PRIMARY KEY,
        tournament_id INTEGER,
        angler1_id INTEGER,
        angler2_id INTEGER,
        total_weight DECIMAL DEFAULT 0.0,
        place_finish INTEGER
    )""",
    """news(
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        author_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        published BOOLEAN DEFAULT 0,
        priority INTEGER DEFAULT 0,
        expires_at TIMESTAMP
    )""",
    """dues(
        id INTEGER PRIMARY KEY,
        angler_id INTEGER,
        year INTEGER NOT NULL,
        amount DECIMAL DEFAULT 25.00,
        paid_date DATE,
        paid BOOLEAN DEFAULT 0,
        UNIQUE(angler_id, year)
    )""",
    """officers(
        id INTEGER PRIMARY KEY,
        angler_id INTEGER,
        position TEXT NOT NULL,
        year INTEGER NOT NULL,
        elected_date DATE,
        UNIQUE(position, year)
    )""",
    """calendar_events(
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        event_date DATE NOT NULL,
        event_type TEXT NOT NULL CHECK (event_type IN ('holiday', 'sabc_tournament', 'other_tournament')),
        description TEXT,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
]

# SQL View definitions for calculations
TOURNAMENT_STANDINGS_VIEW = """
tournament_standings AS
SELECT
    t.id as tournament_id,
    a.name as angler_name,
    a.id as angler_id,
    r.num_fish,
    (r.total_weight - r.dead_fish_penalty) as final_weight,
    r.big_bass_weight,
    r.disqualified,
    r.buy_in,
    RANK() OVER (
        PARTITION BY t.id
        ORDER BY
            CASE WHEN r.disqualified THEN 0
                 WHEN r.buy_in THEN 0
                 ELSE (r.total_weight - r.dead_fish_penalty)
            END DESC
    ) as place,
    CASE
        WHEN r.disqualified THEN 0
        WHEN r.buy_in THEN MAX(0, (
            SELECT 101 - COUNT(*)
            FROM results r2
            WHERE r2.tournament_id = t.id
            AND (r2.total_weight - r2.dead_fish_penalty) > 0
            AND NOT r2.disqualified
            AND NOT r2.buy_in
        ) - 4)
        WHEN (r.total_weight - r.dead_fish_penalty) = 0 THEN MAX(0, (
            SELECT 101 - COUNT(*)
            FROM results r2
            WHERE r2.tournament_id = t.id
            AND (r2.total_weight - r2.dead_fish_penalty) > 0
            AND NOT r2.disqualified
            AND NOT r2.buy_in
        ) - 2)
        ELSE 101 - RANK() OVER (
            PARTITION BY t.id
            ORDER BY (r.total_weight - r.dead_fish_penalty) DESC
        )
    END as points
FROM tournaments t
JOIN results r ON t.id = r.tournament_id
JOIN anglers a ON r.angler_id = a.id
WHERE t.complete = 1 AND a.member = 1
"""

ANGLER_OF_YEAR_VIEW = """
angler_of_year AS
SELECT
    e.year,
    a.name,
    a.id as angler_id,
    SUM(ts.points) as total_points,
    COUNT(DISTINCT t.id) as tournaments_fished,
    SUM(ts.final_weight) as total_weight,
    MAX(r.big_bass_weight) as biggest_bass,
    RANK() OVER (
        PARTITION BY e.year
        ORDER BY SUM(ts.points) DESC
    ) as yearly_rank
FROM tournaments t
JOIN events e ON t.event_id = e.id
JOIN tournament_standings ts ON t.id = ts.tournament_id
JOIN results r ON t.id = r.tournament_id AND ts.angler_id = r.angler_id
JOIN anglers a ON r.angler_id = a.id
WHERE t.complete = 1 AND a.member = 1
GROUP BY e.year, a.id, a.name
ORDER BY e.year DESC, total_points DESC
"""


def init_db():
    """Initialize database with SABC schema."""
    print("Init DB...")
    with engine.connect() as c:
        for table_def in TABLE_DEFINITIONS:
            c.execute(text(f"CREATE TABLE IF NOT EXISTS {table_def}"))
        try:
            c.execute(text("ALTER TABLE anglers ADD COLUMN active BOOLEAN DEFAULT 1"))
        except Exception:
            pass  # Column already exists
        try:
            c.execute(text("ALTER TABLE events ADD COLUMN name TEXT"))
        except Exception:
            pass  # Column already exists
        try:
            c.execute(
                text("ALTER TABLE events ADD COLUMN event_type TEXT DEFAULT 'sabc_tournament'")
            )
        except Exception:
            pass  # Column already exists
        c.commit()


def create_views():
    """Create SQL views for tournament calculations."""
    with engine.connect() as c:
        views = [TOURNAMENT_STANDINGS_VIEW, ANGLER_OF_YEAR_VIEW]
        for view in views:
            c.execute(text(f"CREATE VIEW IF NOT EXISTS {view}"))
        c.commit()


if __name__ == "__main__":
    init_db()
    create_views()
    print("Done!")

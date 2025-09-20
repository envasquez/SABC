import logging
import os

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:dev123@localhost:5432/sabc")

# PostgreSQL engine configuration
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


# PostgreSQL table definitions
def get_table_definitions():
    return [
        """anglers(
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            member BOOLEAN DEFAULT true,
            is_admin BOOLEAN DEFAULT false,
            password_hash TEXT,
            year_joined INTEGER,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """events(
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL UNIQUE,
            year INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            event_type TEXT DEFAULT 'sabc_tournament' CHECK (event_type IN ('sabc_tournament', 'holiday', 'other_tournament', 'club_event')),
            start_time TIME,
            weigh_in_time TIME,
            lake_name TEXT,
            ramp_name TEXT,
            entry_fee DECIMAL DEFAULT 25.00,
            is_cancelled BOOLEAN DEFAULT false,
            holiday_name TEXT
        )""",
        """polls(
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            poll_type TEXT NOT NULL,
            event_id INTEGER,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            starts_at TIMESTAMP NOT NULL,
            closes_at TIMESTAMP NOT NULL,
            closed BOOLEAN DEFAULT false,
            multiple_votes BOOLEAN DEFAULT false,
            winning_option_id INTEGER
        )""",
        """poll_options(
            id SERIAL PRIMARY KEY,
            poll_id INTEGER,
            option_text TEXT NOT NULL,
            option_data TEXT,
            display_order INTEGER DEFAULT 0
        )""",
        """poll_votes(
            id SERIAL PRIMARY KEY,
            poll_id INTEGER,
            option_id INTEGER,
            angler_id INTEGER,
            voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(poll_id, option_id, angler_id)
        )""",
        """tournaments(
            id SERIAL PRIMARY KEY,
            event_id INTEGER,
            poll_id INTEGER,
            name TEXT NOT NULL,
            lake_id INTEGER,
            ramp_id INTEGER,
            lake_name TEXT,
            ramp_name TEXT,
            start_time TIME,
            end_time TIME,
            fish_limit INTEGER DEFAULT 5,
            entry_fee DECIMAL DEFAULT 25.00,
            is_team BOOLEAN DEFAULT true,
            is_paper BOOLEAN DEFAULT false,
            big_bass_carryover DECIMAL DEFAULT 0.0,
            complete BOOLEAN DEFAULT false,
            created_by INTEGER,
            limit_type TEXT DEFAULT 'angler'
        )""",
        """results(
            id SERIAL PRIMARY KEY,
            tournament_id INTEGER,
            angler_id INTEGER,
            num_fish INTEGER DEFAULT 0,
            total_weight DECIMAL DEFAULT 0.0,
            big_bass_weight DECIMAL DEFAULT 0.0,
            dead_fish_penalty DECIMAL DEFAULT 0.0,
            disqualified BOOLEAN DEFAULT false,
            buy_in BOOLEAN DEFAULT false,
            place_finish INTEGER
        )""",
        """team_results(
            id SERIAL PRIMARY KEY,
            tournament_id INTEGER,
            angler1_id INTEGER,
            angler2_id INTEGER,
            total_weight DECIMAL DEFAULT 0.0,
            place_finish INTEGER
        )""",
        """news(
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            author_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            published BOOLEAN DEFAULT false,
            priority INTEGER DEFAULT 0,
            expires_at TIMESTAMP,
            last_edited_by INTEGER
        )""",
        """dues(
            id SERIAL PRIMARY KEY,
            angler_id INTEGER,
            year INTEGER NOT NULL,
            amount DECIMAL DEFAULT 25.00,
            paid_date DATE,
            paid BOOLEAN DEFAULT false,
            UNIQUE(angler_id, year)
        )""",
        """officer_positions(
            id SERIAL PRIMARY KEY,
            angler_id INTEGER,
            position TEXT NOT NULL,
            year INTEGER NOT NULL,
            elected_date DATE,
            UNIQUE(position, year)
        )""",
        """calendar_events(
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            event_date DATE NOT NULL,
            event_type TEXT NOT NULL CHECK (event_type IN ('holiday', 'sabc_tournament', 'other_tournament')),
            description TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """lakes(
            id SERIAL PRIMARY KEY,
            yaml_key TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            google_maps_iframe TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """ramps(
            id SERIAL PRIMARY KEY,
            lake_id INTEGER,
            name TEXT NOT NULL,
            google_maps_iframe TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """password_reset_tokens(
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES anglers(id) ON DELETE CASCADE,
            token VARCHAR(255) NOT NULL UNIQUE,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used_at TIMESTAMP NULL
        )""",
    ]


# PostgreSQL view definitions
def get_tournament_standings_view():
    return """
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
            CASE WHEN r.disqualified = TRUE THEN 0
                 WHEN r.buy_in = TRUE THEN 0
                 ELSE (r.total_weight - r.dead_fish_penalty)
            END DESC
    ) as place,
    CASE
        WHEN r.disqualified = TRUE THEN 0
        WHEN r.buy_in = TRUE THEN GREATEST(0, (
            SELECT 101 - COUNT(*)
            FROM results r2
            WHERE r2.tournament_id = t.id
            AND (r2.total_weight - r2.dead_fish_penalty) > 0
            AND r2.disqualified = FALSE
            AND r2.buy_in = FALSE
        ) - 4)
        WHEN (r.total_weight - r.dead_fish_penalty) = 0 THEN GREATEST(0, (
            SELECT 101 - COUNT(*)
            FROM results r2
            WHERE r2.tournament_id = t.id
            AND (r2.total_weight - r2.dead_fish_penalty) > 0
            AND r2.disqualified = FALSE
            AND r2.buy_in = FALSE
        ) - 2)
        ELSE 101 - RANK() OVER (
            PARTITION BY t.id
            ORDER BY (r.total_weight - r.dead_fish_penalty) DESC
        )
    END as points
FROM tournaments t
JOIN results r ON t.id = r.tournament_id
JOIN anglers a ON r.angler_id = a.id
WHERE t.complete = TRUE AND a.member = TRUE
"""


def get_angler_of_year_view():
    return """
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
WHERE t.complete = TRUE AND a.member = TRUE
GROUP BY e.year, a.id, a.name
ORDER BY e.year DESC, total_points DESC
"""


def create_all_tables():
    """Create all PostgreSQL tables."""
    logger.info("Creating PostgreSQL database tables...")
    table_definitions = get_table_definitions()

    with engine.connect() as c:
        # Create tables
        for table_def in table_definitions:
            c.execute(text(f"CREATE TABLE IF NOT EXISTS {table_def}"))
        c.commit()

        # Create views
        create_views_internal(c)
        c.commit()


def drop_all_tables():
    """Drop all tables and views."""
    logger.info("Dropping all PostgreSQL tables and views...")
    with engine.connect() as c:
        # Drop views first
        c.execute(text("DROP VIEW IF EXISTS tournament_standings CASCADE"))
        c.execute(text("DROP VIEW IF EXISTS angler_of_year CASCADE"))

        # Drop all tables (CASCADE will handle dependencies)
        tables = [
            "password_reset_tokens",
            "poll_votes",
            "poll_options",
            "polls",
            "team_results",
            "results",
            "tournaments",
            "events",
            "ramps",
            "lakes",
            "anglers",
        ]
        for table in tables:
            c.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
        c.commit()


def init_db():
    """Initialize the database with all tables."""
    create_all_tables()


def create_views():
    """Create database views."""
    with engine.connect() as c:
        create_views_internal(c)
        c.commit()


def create_views_internal(connection):
    """Create database views (internal function)."""
    views = [get_tournament_standings_view(), get_angler_of_year_view()]
    for view in views:
        # PostgreSQL doesn't support CREATE VIEW IF NOT EXISTS
        view_name = view.split(" AS")[0].strip().split()[-1]  # Extract view name
        try:
            connection.execute(text(f"DROP VIEW IF EXISTS {view_name} CASCADE"))
            connection.execute(text(f"CREATE VIEW {view}"))
        except Exception as e:
            logger.warning(f"Failed to create view {view_name}: {e}")


if __name__ == "__main__":
    create_all_tables()
    logger.info("PostgreSQL database initialization complete!")

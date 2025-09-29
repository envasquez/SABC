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
            place_finish INTEGER,
            UNIQUE(tournament_id, angler_id)
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


def create_all_tables():
    """Create all PostgreSQL tables."""
    logger.info("Creating PostgreSQL database tables...")
    table_definitions = get_table_definitions()

    with engine.connect() as c:
        # Create tables
        for table_def in table_definitions:
            c.execute(text(f"CREATE TABLE IF NOT EXISTS {table_def}"))
        c.commit()


def drop_all_tables():
    """Drop all tables."""
    logger.info("Dropping all PostgreSQL tables...")
    with engine.connect() as c:
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


if __name__ == "__main__":
    create_all_tables()
    logger.info("PostgreSQL database initialization complete!")

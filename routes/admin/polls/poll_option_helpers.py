"""Poll option update helpers."""

from routes.dependencies import db


def update_or_create_poll_option(poll_id: int, option_text: str, option_id: str | None) -> None:
    """Update existing poll option or create new one."""
    if not option_text:
        return

    if option_id:
        # Update existing option
        db(
            """UPDATE poll_options
               SET option_text = :option_text
               WHERE id = :option_id AND poll_id = :poll_id""",
            {"option_text": option_text, "option_id": option_id, "poll_id": poll_id},
        )
    else:
        # Create new option
        db(
            """INSERT INTO poll_options (poll_id, option_text, option_data)
               VALUES (:poll_id, :option_text, :option_data)""",
            {"poll_id": poll_id, "option_text": option_text, "option_data": "{}"},
        )

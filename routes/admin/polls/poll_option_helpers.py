from sqlalchemy.exc import IntegrityError

from core.db_schema import PollOption, get_session
from core.helpers.logging import get_logger

logger = get_logger("admin.polls.helpers")


def update_or_create_poll_option(poll_id: int, option_text: str, option_id: str | None) -> None:
    """Update or create a poll option, preserving the ID when updating.

    Args:
        poll_id: The poll ID this option belongs to
        option_text: The text for the option
        option_id: The existing option ID if updating, None if creating
    """
    if not option_text:
        return

    with get_session() as session:
        if option_id:
            # Update existing poll option
            poll_option = (
                session.query(PollOption)
                .filter(PollOption.id == int(option_id), PollOption.poll_id == poll_id)
                .first()
            )
            if poll_option:
                # Check if the text is actually changing
                if poll_option.option_text == option_text:
                    # No change needed
                    return

                # Check if another option already has this text
                existing_with_text = (
                    session.query(PollOption)
                    .filter(
                        PollOption.poll_id == poll_id,
                        PollOption.option_text == option_text,
                        PollOption.id != int(option_id),
                    )
                    .first()
                )

                if existing_with_text:
                    logger.warning(
                        "Cannot update option text - duplicate text exists",
                        extra={
                            "poll_id": poll_id,
                            "option_id": option_id,
                            "new_text": option_text,
                            "existing_option_id": existing_with_text.id,
                        },
                    )
                    return

                # Safe to update
                poll_option.option_text = option_text
                logger.info(
                    "Updated poll option text",
                    extra={"poll_id": poll_id, "option_id": option_id, "new_text": option_text},
                )
        else:
            # Create new poll option
            try:
                new_option = PollOption(poll_id=poll_id, option_text=option_text, option_data="{}")
                session.add(new_option)
                session.flush()
                logger.info(
                    "Created new poll option",
                    extra={
                        "poll_id": poll_id,
                        "option_id": new_option.id,
                        "option_text": option_text,
                    },
                )
            except IntegrityError as e:
                logger.error(
                    "Failed to create poll option - duplicate text",
                    extra={"poll_id": poll_id, "option_text": option_text, "error": str(e)},
                )
                session.rollback()

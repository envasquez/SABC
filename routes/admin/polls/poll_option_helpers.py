from core.db_schema import PollOption, get_session


def update_or_create_poll_option(poll_id: int, option_text: str, option_id: str | None) -> None:
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
                poll_option.option_text = option_text
        else:
            # Create new poll option
            new_option = PollOption(poll_id=poll_id, option_text=option_text, option_data="{}")
            session.add(new_option)

"""normalize_phone_numbers

Revision ID: c32bccfde319
Revises: 93c0050661d1
Create Date: 2026-02-20 10:12:04.621435

"""

from typing import Optional, Sequence, Union

from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c32bccfde319"
down_revision: Union[str, None] = "93c0050661d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def format_phone(phone: Optional[str]) -> Optional[str]:
    """Format phone number to (XXX) XXX-XXXX format.

    This matches the validation logic in routes/auth/validation.py
    """
    if not phone:
        return None
    # Extract only digits
    digits = "".join(c for c in phone if c.isdigit())
    if not digits:
        return None
    # Handle 11-digit numbers starting with 1 (country code)
    if len(digits) == 11 and digits[0] == "1":
        digits = digits[1:]
    # Format 10-digit numbers
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    # Return original if can't format (wrong number of digits)
    return phone


def upgrade() -> None:
    """Normalize all phone numbers to (XXX) XXX-XXXX format."""
    conn = op.get_bind()

    # Fetch all anglers with phone numbers
    result = conn.execute(
        text("SELECT id, phone FROM anglers WHERE phone IS NOT NULL AND phone != ''")
    )
    rows = result.fetchall()

    # Update each phone number
    for row in rows:
        angler_id, phone = row
        formatted = format_phone(phone)
        if formatted and formatted != phone:
            conn.execute(
                text("UPDATE anglers SET phone = :phone WHERE id = :id"),
                {"phone": formatted, "id": angler_id},
            )


def downgrade() -> None:
    """No downgrade - phone formatting is not reversible."""
    # Phone numbers cannot be un-formatted since original format is lost
    pass

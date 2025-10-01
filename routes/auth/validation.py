from typing import Optional


def validate_phone_number(phone: Optional[str]) -> tuple[bool, Optional[str], Optional[str]]:
    if not phone:
        return True, None, None

    phone_digits = "".join(filter(str.isdigit, phone.strip()))

    if not phone_digits:
        return True, None, None

    if len(phone_digits) == 11 and phone_digits[0] == "1":
        phone_digits = phone_digits[1:]

    if len(phone_digits) == 10:
        return True, f"({phone_digits[:3]}) {phone_digits[3:6]}-{phone_digits[6:]}", None
    elif len(phone_digits) < 10:
        return False, None, "Phone number must have 10 digits"
    else:
        return False, None, "Phone number has too many digits"

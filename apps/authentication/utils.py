def normalize_phone(phone: str) -> str:
    phone = phone.strip()
    phone = phone.replace("+", "")
    phone = phone.replace(" ", "")
    phone = phone.replace("-", "")
    phone = phone.replace("(", "")
    phone = phone.replace(")", "")

    return phone

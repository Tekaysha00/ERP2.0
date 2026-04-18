def format_classname(value):
    if not value:
        return value

    v = str(value).strip().lower().replace(" ", "")
    num = ''.join(filter(str.isdigit, v))

    if num:
        return f"Class {num}"
    
    return value

FIELDS = ("id", "title", "status")


def _clean(value):
    if value is None:
        return ""
    return str(value).strip()


def format_task_summary(task):
    normalized = {field: _clean(task.get(field)) for field in FIELDS}
    return " | ".join(f"{field}={normalized[field]}" for field in FIELDS)

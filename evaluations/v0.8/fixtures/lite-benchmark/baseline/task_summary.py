FIELDS = ("id", "title", "status")


def _clean(value):
    if value is None:
        return ""
    return str(value).strip()


def format_task_summary(task):
    return (
        f"id={_clean(task.get('id'))} | "
        f"title={_clean(task.get('title'))} | "
        f"status={_clean(task.get('status'))}"
    )

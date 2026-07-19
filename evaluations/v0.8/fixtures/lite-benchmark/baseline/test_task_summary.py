import unittest

from task_summary import FIELDS, format_task_summary


class TaskSummaryTests(unittest.TestCase):
    def test_fields_are_stable(self):
        self.assertEqual(("id", "title", "status"), FIELDS)

    def test_formats_and_trims_known_fields(self):
        task = {"id": "  LEAN-002 ", "title": "  Prototype  ", "status": " Ready "}
        self.assertEqual(
            "id=LEAN-002 | title=Prototype | status=Ready",
            format_task_summary(task),
        )

    def test_missing_and_none_values_are_empty(self):
        self.assertEqual(
            "id= | title= | status=",
            format_task_summary({"id": None}),
        )

    def test_unknown_fields_are_ignored(self):
        task = {"id": 7, "title": "Task", "status": "Done", "extra": "ignore"}
        self.assertEqual(
            "id=7 | title=Task | status=Done",
            format_task_summary(task),
        )


if __name__ == "__main__":
    unittest.main()

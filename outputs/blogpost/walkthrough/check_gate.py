"""Small deterministic checks of gate behavior; no API calls."""
import contextlib
import io
import unittest

from drug_discovery import TESTS, print_report


class GateChecks(unittest.TestCase):
    def gate(self, accuracy_a, accuracy_b):
        rows = [
            dict(question=q, version=v, trial=1,
                 accuracy=score, clarity=2, reason="Fixture")
            for q, _ in TESTS
            for v, score in (("A", accuracy_a), ("B", accuracy_b))
        ]
        with contextlib.redirect_stdout(io.StringIO()):
            return print_report(rows)["passed"]

    def test_complete_answers_pass(self):
        self.assertTrue(self.gate(2, 2))

    def test_accuracy_drop_fails(self):
        self.assertFalse(self.gate(2, 1))

    def test_equal_major_errors_fail(self):
        self.assertFalse(self.gate(0, 0))

    def test_shared_incompleteness_passes_relative_gate(self):
        self.assertTrue(self.gate(1, 1))


if __name__ == "__main__":
    unittest.main()

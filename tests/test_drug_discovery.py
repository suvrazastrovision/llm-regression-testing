"""Offline behavioral checks: no credentials, model requests, or trace uploads."""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

# Direct execution puts tests/ on the import path; also include the repo root.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import ContentFilterFinishReasonError, LengthFinishReasonError

import drug_discovery as d


def scored_rows(a=2, b=2, repeats=1):
    return [dict(question=question, version=version, trial=trial,
                 accuracy=accuracy, clarity=2, reason="Fixture score")
            for question, _ in d.TESTS for trial in range(1, repeats + 1)
            for version, accuracy in (("A", a), ("B", b))]


class ReportTests(unittest.TestCase):
    def report(self, rows, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return d.print_report(rows, **kwargs)

    def test_matching_complete_answers_pass(self):
        self.assertTrue(self.report(scored_rows())["passed"])

    def test_accuracy_drop_fails_even_when_other_question_improves(self):
        rows = scored_rows()
        rows[1]["accuracy"] = 1
        rows[2]["accuracy"] = 1
        gate = self.report(rows)
        self.assertFalse(gate["passed"])
        self.assertFalse(gate["comparisons"][0]["passed"])
        self.assertTrue(gate["comparisons"][1]["passed"])

    def test_equal_major_errors_still_fail(self):
        self.assertFalse(self.report(scored_rows(a=0, b=0))["passed"])

    def test_matching_incomplete_answers_pass_relative_gate(self):
        self.assertTrue(self.report(scored_rows(a=1, b=1))["passed"])

    def test_clarity_does_not_change_accuracy_gate(self):
        rows = scored_rows()
        rows[1]["clarity"] = 0
        self.assertTrue(self.report(rows)["passed"])

    def test_repeats_compare_question_means(self):
        rows = scored_rows(repeats=2)
        rows[0]["accuracy"] = 1
        rows[3]["accuracy"] = 1
        gate = self.report(rows, repeats=2)
        self.assertTrue(gate["passed"])
        self.assertEqual(gate["comparisons"][0]["accuracy_a"], 1.5)
        self.assertEqual(gate["comparisons"][0]["accuracy_b"], 1.5)

    def test_major_error_is_not_hidden_by_mean(self):
        rows = scored_rows(a=1, repeats=2)
        rows[1]["accuracy"] = 0
        self.assertFalse(self.report(rows, repeats=2)["passed"])

    def test_missing_duplicate_and_unscored_rows_are_rejected(self):
        unscored = scored_rows()
        del unscored[0]["accuracy"]
        for rows in (scored_rows()[:-1], [scored_rows()[0]] * 4, unscored):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.report(rows)


class ResponseTests(unittest.TestCase):
    def client(self, *, content=" Answer ", refusal=None, finish="stop", parsed=None):
        client = Mock()
        response = SimpleNamespace(choices=[SimpleNamespace(
            finish_reason=finish,
            message=SimpleNamespace(content=content, refusal=refusal, parsed=parsed))])
        client.chat.completions.create.return_value = response
        client.chat.completions.parse.return_value = response
        return client

    def test_answer_is_stripped(self):
        self.assertEqual(d.generate_answer(self.client(), "model", "prompt"), "Answer")

    def test_empty_and_truncated_answers_are_not_scored(self):
        for client in (self.client(content=" "), self.client(finish="length")):
            with self.subTest(client=client), self.assertRaises(ValueError):
                d.generate_answer(client, "model", "prompt")

    def test_refusal_is_preserved_for_accuracy_judging(self):
        client = self.client(content=None, refusal="I cannot answer.")
        self.assertEqual(d.generate_answer(client, "model", "prompt"), "I cannot answer.")

    def test_missing_choices_are_rejected(self):
        client = self.client()
        client.chat.completions.create.return_value.choices = []
        with self.assertRaises(ValueError):
            d.generate_answer(client, "model", "prompt")
        with self.assertRaises(ValueError):
            d.score_answer(client, "judge", "question", "facts", "answer")

    def test_invalid_judge_responses_are_rejected(self):
        blank = d.Score(accuracy=2, clarity=2, reason=" ")
        valid = d.Score(accuracy=2, clarity=2, reason="Correct")
        for client in (self.client(), self.client(parsed=blank),
                       self.client(parsed=valid, refusal="Cannot judge")):
            with self.subTest(client=client), self.assertRaises(ValueError):
                d.score_answer(client, "judge", "question", "facts", "answer")

    def test_judge_receives_data_without_version_label(self):
        score = d.Score(accuracy=2, clarity=2, reason="Correct")
        client = self.client(parsed=score)
        self.assertEqual(d.score_answer(client, "judge", "q", "f", "a"), score)
        messages = client.chat.completions.parse.call_args.kwargs["messages"]
        self.assertEqual(json.loads(messages[1]["content"]),
                         {"question": "q", "required_facts": "f", "answer": "a"})


class MainTests(unittest.TestCase):
    def run_main(self, *, scores=None, error=None, argv=None, flush_error=None):
        with tempfile.TemporaryDirectory() as folder, contextlib.ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {
                "OPENAI_API_KEY": "mock", "LANGFUSE_PUBLIC_KEY": "mock",
                "LANGFUSE_SECRET_KEY": "mock"}, clear=True))
            stack.enter_context(patch.object(d, "load_dotenv"))
            stack.enter_context(patch.object(d, "__file__", str(Path(folder) / "app.py")))
            trace = Mock()
            langfuse = Mock()
            langfuse.start_as_current_observation.side_effect = (
                lambda **kwargs: contextlib.nullcontext(trace))
            langfuse.flush.side_effect = flush_error
            stack.enter_context(patch.object(d, "get_client", return_value=langfuse))
            stack.enter_context(patch.object(d, "OpenAI", return_value=contextlib.nullcontext(Mock())))
            generate = stack.enter_context(patch.object(d, "generate_answer", return_value="Saved answer"))
            judge = stack.enter_context(patch.object(d, "score_answer"))
            judge.side_effect = error or scores
            judge.return_value = d.Score(accuracy=2, clarity=2, reason="Correct")
            output = stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            code = d.main(argv or [])
            files = list((Path(folder) / "results").glob("*.json"))
            self.assertEqual(len(files), 1)
            rows = json.loads(files[0].read_text(encoding="utf-8"))
            langfuse.flush.assert_called_once()
            return code, output.getvalue(), rows, generate.call_args_list

    def test_pass_returns_zero(self):
        code, output, rows, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("Regression gate: PASS", output)
        self.assertEqual(len(rows), 4)

    def test_regression_returns_two_and_saves_all_answers(self):
        scores = [d.Score(accuracy=x, clarity=2, reason="Fixture") for x in (2, 0, 0, 2)]
        code, output, rows, _ = self.run_main(scores=scores)
        self.assertEqual(code, 2)
        self.assertIn("Regression gate: FAIL", output)
        self.assertEqual(len(rows), 4)

    def test_judge_failures_return_one_and_preserve_partial_answers(self):
        for error, diagnostic in (
            (ValueError("Invalid scores"), "Invalid scores"),
            (LengthFinishReasonError(completion=SimpleNamespace(usage=None)), "truncated"),
            (ContentFilterFinishReasonError(), "content filter"),
        ):
            with self.subTest(error=type(error).__name__):
                code, output, rows, _ = self.run_main(error=error)
                self.assertEqual(code, 1)
                self.assertIn(diagnostic, output)
                self.assertNotIn("Regression gate:", output)
                self.assertEqual(rows[0]["answer"], "Saved answer")
                self.assertNotIn("accuracy", rows[0])

    def test_comparison_repeats_do_not_supply_answer_keys(self):
        code, _, rows, calls = self.run_main(argv=["--mode", "comparison", "--repeats", "2"])
        self.assertEqual(code, 0)
        self.assertEqual(len(rows), 8)
        self.assertEqual({row["trial"] for row in rows}, {1, 2})
        self.assertEqual([row["version"] for row in rows], ["A", "B", "B", "A", "B", "A", "A", "B"])
        for call in calls:
            prompt = call.args[2]
            for _, facts in d.TESTS:
                self.assertNotIn(facts, prompt)
            self.assertNotIn("False claim:", prompt)
        self.assertTrue(all(row["mode"] == "comparison" for row in rows))

    def test_trace_flush_failure_does_not_replace_success(self):
        code, output, rows, _ = self.run_main(flush_error=RuntimeError("Offline"))
        self.assertEqual(code, 0)
        self.assertIn("Langfuse upload did not finish", output)
        self.assertEqual(len(rows), 4)

    def test_invalid_repeat_counts_are_rejected_before_credentials(self):
        for value in ("0", "-1", "abc"):
            with self.subTest(value=value), patch.object(d, "load_dotenv") as load, \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                d.main(["--repeats", value])
            self.assertEqual(error.exception.code, 2)
            load.assert_not_called()


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class AgentEvaluationTests(unittest.TestCase):
    def test_dataset_has_balanced_research_cases(self):
        from scripts.evaluate_agent_tools import load_cases

        cases = load_cases(PROJECT_ROOT / "knowledge_base" / "evaluation" / "agent_tool_cases.jsonl")
        categories = {case["category"] for case in cases}

        self.assertGreaterEqual(len(cases), 30)
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        self.assertTrue({"fit", "status", "cancel", "service", "no_tool", "recovery"} <= categories)
        self.assertGreaterEqual(sum(case["expected_tool"] is None for case in cases), 10)
        self.assertGreaterEqual(sum("prior_failure" in case for case in cases), 8)

    def test_ablation_strategies_change_only_intended_context(self):
        from scripts.evaluate_agent_tools import build_messages

        case = {
            "id": "repair",
            "question": "修正后继续",
            "data_available": True,
            "prior_failure": {
                "tool": "start_symbolic_regression",
                "arguments": {"niterations": 10000},
                "error": "too large",
            },
        }
        skill = SimpleNamespace(name="symbolic_regression", instructions="使用工具读取真实状态。")
        schema_only = build_messages(case, skill, "schema_only")
        feedback = build_messages(case, skill, "skill_feedback")
        guided = build_messages(case, skill, "guided_repair")

        self.assertFalse(any(message["role"] == "tool" for message in schema_only))
        self.assertTrue(any(message["role"] == "tool" for message in feedback))
        self.assertFalse(any("不要重复完全相同" in str(message.get("content")) for message in feedback))
        self.assertTrue(any("不要重复完全相同" in str(message.get("content")) for message in guided))

    def test_argument_rules_and_recovery_require_a_changed_valid_call(self):
        from scripts.evaluate_agent_tools import arguments_match, recovery_succeeds

        case = {
            "expected_tool": "start_symbolic_regression",
            "argument_rules": {"niterations": {"minimum": 1, "maximum": 300, "not_equals": 10000}},
            "prior_failure": {
                "tool": "start_symbolic_regression",
                "arguments": {"niterations": 10000},
            },
        }

        self.assertTrue(arguments_match(case, {"niterations": 100}))
        self.assertFalse(arguments_match(case, {"niterations": 10000}))
        self.assertTrue(recovery_succeeds(case, "start_symbolic_regression", {"niterations": 100}, True))
        self.assertFalse(recovery_succeeds(case, "start_symbolic_regression", {"niterations": 10000}, False))

    def test_summarizer_preserves_raw_data_and_creates_derived_artifacts(self):
        from scripts.evaluate_agent_tools import summarize_strategy
        from scripts.summarize_agent_experiment import summarize

        raw = []
        for strategy, success in (("schema_only", False), ("skill_feedback", True), ("guided_repair", True)):
            raw.append({
                "id": "repair-case",
                "category": "recovery",
                "strategy": strategy,
                "repetition": 1,
                "skill": "symbolic_regression",
                "expected_tool": "start_symbolic_regression",
                "actual_tool": "start_symbolic_regression" if success else None,
                "tool_call_count": 1 if success else 0,
                "tool_correct": success,
                "schema_valid": True if success else None,
                "schema_error": None,
                "arguments": {"niterations": 100} if success else None,
                "argument_correct": success,
                "recovery_case": True,
                "recovery_success": success,
                "end_to_end_success": success,
                "unnecessary_call": False,
                "latency_ms": 100.0,
                "request_error": None,
            })

        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            summary = {
                "run_id": "test-run",
                "created_at": "2026-08-20T00:00:00+00:00",
                "research_question": "test",
                "hypothesis": "test",
                "dataset": {"case_count": 1, "sha256": "abc"},
                "code": {"commit": "abc", "dirty": True},
                "environment": {"model": "fake"},
                "config": {"strategies": ["schema_only", "skill_feedback", "guided_repair"],
                           "repetitions": 1, "temperature": 0, "enable_thinking": False},
                "summaries": {
                    strategy: summarize_strategy([item for item in raw if item["strategy"] == strategy], 7)
                    for strategy in ("schema_only", "skill_feedback", "guided_repair")
                },
            }
            (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            raw_path = run_dir / "raw_results.jsonl"
            raw_text = "".join(json.dumps(item) + "\n" for item in raw)
            raw_path.write_text(raw_text, encoding="utf-8")

            summarize(run_dir)

            self.assertEqual(raw_path.read_text(encoding="utf-8"), raw_text)
            for name in ("metrics.csv", "case_results.csv", "category_metrics.csv", "ablation_metrics.svg",
                         "REPORT.md", "RESUME_CLAIMS.md"):
                self.assertTrue((run_dir / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()

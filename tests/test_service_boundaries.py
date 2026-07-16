import asyncio
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ServiceBoundaryTests(unittest.TestCase):
    def test_ai_import_does_not_load_compute_stack(self):
        probe = (
            "import sys; import ai_module.main; "
            "forbidden=('pysr_module','analysis_module','pysr','numpy','pandas','matplotlib'); "
            "loaded=[name for name in sys.modules if name.split('.')[0] in forbidden]; "
            "print(loaded); raise SystemExit(1 if loaded else 0)"
        )
        result = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rag_service_import_keeps_large_models_lazy(self):
        probe = (
            "import sys; import rag_module.service; "
            "forbidden=('FlagEmbedding','torch','transformers'); "
            "loaded=[name for name in sys.modules if name.split('.')[0] in forbidden]; "
            "print(loaded); raise SystemExit(1 if loaded else 0)"
        )
        result = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_importing_config_has_no_filesystem_side_effect(self):
        probe = (
            "import os, tempfile; from pathlib import Path; "
            "root=Path(tempfile.mkdtemp())/'must-not-exist'; "
            "os.environ['DATA_DIR']=str(root); import config; "
            "print(root.exists()); raise SystemExit(1 if root.exists() else 0)"
        )
        result = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_compute_and_ai_routes_are_disjoint(self):
        from ai_module.app_factory import create_ai_app
        from analysis_module.app_factory import create_compute_app

        ai_paths = {route.path for route in create_ai_app().routes}
        compute_paths = {route.path for route in create_compute_app().routes}

        self.assertIn("/analyze_experiment", ai_paths)
        self.assertNotIn("/analyze_experiment", compute_paths)
        self.assertIn("/analyze_data", compute_paths)
        self.assertIn("/tasks", compute_paths)
        self.assertNotIn("/tasks", ai_paths)

    def test_numeric_table_parser_supports_common_delimiters(self):
        from analysis_module.routes import parse_numeric_table

        for text in ("1,2\n2,4\n", "1 2\n2 4\n", "1\t2\n2\t4\n"):
            frame = parse_numeric_table(text)
            self.assertEqual(frame.shape, (2, 2))

    def test_worker_parallelism_is_managed_by_server_settings(self):
        from config import settings
        from pysr_module.task_worker import _get_model_parameters

        params = _get_model_parameters({
            "niterations": 25,
            "procs": 64,
            "populations": 256,
            "parallelism": "multiprocessing",
        })

        self.assertEqual(params["niterations"], 25)
        self.assertEqual(params["procs"], settings.PYSR_PROCS_PER_TASK)
        self.assertEqual(params["parallelism"], settings.PYSR_PARALLELISM)
        self.assertGreaterEqual(params["populations"], params["procs"] + 1)

    def test_worker_keeps_tournament_smaller_than_population(self):
        from pysr_module.task_worker import _get_model_parameters

        small = _get_model_parameters({
            "population_size": 5,
            "tournament_selection_n": 999,
        })
        default = _get_model_parameters({})

        self.assertEqual(small["population_size"], 5)
        self.assertEqual(small["tournament_selection_n"], 4)
        self.assertLess(small["tournament_selection_n"], small["population_size"])
        self.assertEqual(default["tournament_selection_n"], 15)

    def test_release_packages_keep_service_boundaries(self):
        from scripts.build_release import PACKAGE_SPECS, _package_files

        package_paths = {
            spec.name: {archive_path for _, archive_path in _package_files(spec)}
            for spec in PACKAGE_SPECS
        }
        compute = package_paths["guidelab-compute"]
        ai = package_paths["guidelab-ai"]
        knowledge = package_paths["guidelab-knowledge"]
        web = package_paths["guidelab-web"]

        self.assertTrue(any(path.startswith("analysis_module/") for path in compute))
        self.assertTrue(any(path.startswith("pysr_module/") for path in compute))
        self.assertFalse(any(path.startswith("ai_module/") for path in compute))
        self.assertFalse(any("julia-1.11.6" in path for path in compute))

        self.assertTrue(any(path.startswith("ai_module/") for path in ai))
        self.assertTrue(any(path.startswith("rag_module/") for path in ai))
        self.assertIn("scripts/ingest_knowledge.py", ai)
        self.assertIn("scripts/test_rag.py", ai)
        self.assertIn("scripts/evaluate_rag.py", ai)
        self.assertFalse(any(path.startswith("pysr_module/") for path in ai))
        self.assertFalse(any(path.startswith("analysis_module/") for path in ai))
        self.assertFalse(any(path.startswith("knowledge_base/") for path in ai))

        self.assertTrue(any(path.startswith("knowledge_base/raw_docs/") for path in knowledge))
        self.assertIn("knowledge_base/evaluation/rag_queries.jsonl", knowledge)
        self.assertFalse(any("vector_store" in path for path in knowledge))
        self.assertFalse(any("model_cache" in path for path in knowledge))
        self.assertFalse(any(path.endswith(".ingestion_index.json") for path in knowledge))

        self.assertTrue(any(path.startswith("dist/") for path in web))
        self.assertIn("nginx/guidelab-locations.conf", web)

    def test_agent_submits_bound_data_to_compute_service(self):
        from ai_module.agent import build_default_registries

        tools, _ = build_default_registries()
        context = {
            "data_text": "1\t2\n2\t4\n",
            "session_token": "signed-classroom-token",
            "variable_mapping": {
                "x_variables": [{"index": 0, "name": "length", "pysr_name": "x0"}],
                "y_variable": {"name": "period", "pysr_name": "y"},
            },
        }

        with patch(
            "ai_module.agent.capabilities._compute_request",
            return_value={"task_id": "task-from-agent"},
        ) as request:
            execution = asyncio.run(
                tools.execute(
                    "start_symbolic_regression",
                    {"niterations": 25},
                    allowed_tools=("start_symbolic_regression",),
                    context=context,
                )
            )
            repeated = asyncio.run(
                tools.execute(
                    "start_symbolic_regression",
                    {},
                    allowed_tools=("start_symbolic_regression",),
                    context=context,
                )
            )

        self.assertTrue(execution.ok, execution.error)
        self.assertEqual(execution.output["task_id"], "task-from-agent")
        self.assertEqual(repeated.output["status"], "already_submitted")
        request.assert_called_once()
        args, kwargs = request.call_args
        self.assertEqual(args, ("POST", "/tasks"))
        self.assertEqual(kwargs["session_token"], "signed-classroom-token")
        self.assertEqual(kwargs["files"]["file"][1].decode("utf-8"), context["data_text"].strip())
        params = json.loads(kwargs["data"]["params"])
        self.assertEqual(params["niterations"], 25)
        self.assertEqual(params["variable_mapping"], context["variable_mapping"])

    def test_agent_rejects_tool_arguments_outside_json_schema(self):
        from ai_module.agent import build_default_registries

        tools, _ = build_default_registries()
        execution = asyncio.run(
            tools.execute(
                "start_symbolic_regression",
                {"niterations": 10_000, "unexpected": True},
                allowed_tools=("start_symbolic_regression",),
                context={"data_text": "1,2\n2,4\n"},
            )
        )

        self.assertFalse(execution.ok)
        self.assertIn("Schema", execution.error)

    def test_agent_runner_can_start_pysr_from_conversation_data(self):
        from ai_module.agent import AgentRunner, build_default_registries

        responses = iter([
            {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": "call-fit",
                            "type": "function",
                            "function": {
                                "name": "start_symbolic_regression",
                                "arguments": json.dumps({"niterations": 30}),
                            },
                        }],
                    }
                }]
            },
            {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": "拟合任务已提交，任务 ID 是 agent-task。",
                    }
                }]
            },
        ])

        async def fake_completion(_payload, _config):
            return next(responses)

        tools, skills = build_default_registries()
        runner = AgentRunner(tools, skills, completion=fake_completion)
        with patch(
            "ai_module.agent.capabilities._compute_request",
            return_value={"task_id": "agent-task"},
        ):
            result = asyncio.run(runner.run(
                system_prompt="你是实验助手。",
                messages=[{"role": "user", "content": "请拟合当前数据"}],
                skill_name="physics_experiment",
                provider_config={
                    "model": "fake-model",
                    "temperature": 0,
                    "max_tokens": 100,
                    "timeout": 1,
                },
                tool_context={"data_text": "1\t2\n2\t4\n"},
            ))

        self.assertIn("agent-task", result.content)
        self.assertEqual(result.trace[0]["tool"], "start_symbolic_regression")
        self.assertTrue(result.trace[0]["ok"])
        self.assertEqual(result.trace[0]["task_id"], "agent-task")


if __name__ == "__main__":
    unittest.main()

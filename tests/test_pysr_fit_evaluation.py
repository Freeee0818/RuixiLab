import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from pysr_module.fit_evaluation import evaluate_equation_fit, predict_equation


class PySRFitEvaluationTests(unittest.TestCase):
    def test_exact_linear_equation_has_strong_in_sample_evidence(self):
        X = np.arange(10, dtype=float).reshape(-1, 1)
        y = 2 * X[:, 0] + 1

        assessment = evaluate_equation_fit("2 * x0 + 1", X, y, complexity=5, max_complexity=20)

        self.assertEqual(assessment["status"], "strong")
        self.assertAlmostEqual(assessment["metrics"]["r2"], 1.0)
        self.assertAlmostEqual(assessment["metrics"]["rmse"], 0.0)
        self.assertEqual(assessment["metrics"]["coverage"], 1.0)
        self.assertIn("量纲一致性", assessment["boundary"])

    def test_multivariate_expression_is_evaluated(self):
        X = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
        prediction = predict_equation("x0 + 2 * x1", X)
        np.testing.assert_allclose(prediction, [5.0, 11.0, 17.0])

    def test_non_finite_domain_is_reported_as_risk(self):
        X = np.array([[-1.0], [1.0], [2.0]])
        y = np.array([0.0, 0.0, np.log(2.0)])

        assessment = evaluate_equation_fit("log(x0)", X, y)

        self.assertEqual(assessment["status"], "weak")
        self.assertAlmostEqual(assessment["metrics"]["coverage"], 2 / 3, places=6)
        self.assertTrue(any("有限预测值" in item for item in assessment["risks"]))

    def test_high_complexity_and_small_sample_are_disclosed(self):
        X = np.arange(8, dtype=float).reshape(-1, 1)
        y = X[:, 0]

        assessment = evaluate_equation_fit("x0", X, y, complexity=9, max_complexity=10)

        self.assertTrue(any("样本量" in item for item in assessment["risks"]))
        self.assertTrue(any("过拟合" in item for item in assessment["risks"]))

    def test_unsafe_expression_is_rejected(self):
        with self.assertRaises(ValueError):
            predict_equation("__import__('os').system('echo unsafe')", np.ones((3, 1)))

    def test_service_attaches_diagnostics_to_each_candidate(self):
        from pysr_module.pysr_service import PySRService

        X = np.arange(10, dtype=float).reshape(-1, 1)
        y = 3 * X[:, 0]
        equations = [{"equation": "3 * x0", "complexity": 3, "score": 0.99, "loss": 0.0}]
        with tempfile.TemporaryDirectory() as temp_dir:
            service = PySRService(output_dir=temp_dir, max_concurrent_tasks=1)
            try:
                with (
                    patch.object(service, "_create_complexity_plot_from_equations", return_value=None),
                    patch.object(service, "_create_single_equation_plot", return_value=None),
                ):
                    result = service._generate_results_from_equations(
                        equations, X, y, "diagnostic-test", {"maxsize": 20}
                    )
            finally:
                service.shutdown()

        self.assertEqual(result["equations"][0]["rationality"]["status"], "strong")
        self.assertEqual(result["fit_evaluation"]["scope"], "observed_samples")


if __name__ == "__main__":
    unittest.main()

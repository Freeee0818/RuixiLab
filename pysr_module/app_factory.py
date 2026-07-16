"""Compatibility import for the compute-service application factory."""

from analysis_module.app_factory import create_compute_app

create_app = create_compute_app

__all__ = ["create_app", "create_compute_app"]

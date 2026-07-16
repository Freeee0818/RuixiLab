#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Compatibility shim for direct starts from inside pysr_module.

Some server panels start this service with:

    cd pysr_module && python main.py

In that mode, ``from config import settings`` resolves to this file instead of
the project-level ``config`` package. Load the real settings module by file
path so the deployment does not depend on the working directory.
"""

from __future__ import annotations

import importlib.util
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_SETTINGS_PATH = os.path.join(PROJECT_ROOT, "config", "settings.py")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

spec = importlib.util.spec_from_file_location("_guidelab_real_settings", REAL_SETTINGS_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"Unable to load GuideLab settings from {REAL_SETTINGS_PATH}")

_settings_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_settings_module)

settings = _settings_module.settings
settings.ensure_compute_directories()

__all__ = ["settings"]

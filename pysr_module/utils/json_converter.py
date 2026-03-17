#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
JSON序列化转换器
用于处理numpy类型和其他非JSON原生类型
"""

import base64
from typing import Any


def json_converter(o: Any) -> Any:
    """Convert numpy types and other non-JSON types to Python native types for JSON serialization."""
    try:
        import numpy as np
    except ImportError:
        np = None

    # numpy scalar types
    if np is not None:
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()

    # bytes -> base64
    if isinstance(o, (bytes, bytearray)):
        return base64.b64encode(o).decode()

    # Fallback: try to use __dict__ or str
    try:
        return o.__dict__
    except Exception:
        return str(o)






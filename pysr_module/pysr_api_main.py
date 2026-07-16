"""Deprecated alias for ``python -m analysis_module.main``."""

from analysis_module.main import app, main

__all__ = ["app", "main"]


if __name__ == "__main__":
    main()

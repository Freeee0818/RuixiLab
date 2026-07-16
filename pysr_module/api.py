"""Compatibility entrypoint; the real compute app lives in analysis_module."""

from analysis_module.main import app, main

__all__ = ["app", "main"]


if __name__ == "__main__":
    main()

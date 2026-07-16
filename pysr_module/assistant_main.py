"""Deprecated alias for ``python -m ai_module.main``."""

from ai_module.main import app, main

__all__ = ["app", "main"]


if __name__ == "__main__":
    main()

"""Independent invitation-account and access-control service."""

def create_access_app():
    # Keep the offline roster importer usable without installing the web server.
    from .app_factory import create_access_app as factory

    return factory()

__all__ = ["create_access_app"]

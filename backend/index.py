"""Vercel discovers this ASGI entrypoint with backend/ as the project root."""

from app.main import app

# This entrypoint is for hosted deployments. Enforce the boundary even if the
# platform's automatic environment variables have been disabled in project settings.
app.state.settings = app.state.settings.model_copy(update={"vercel": True})
app.state.settings.require_hosted_safety()

__all__ = ["app"]

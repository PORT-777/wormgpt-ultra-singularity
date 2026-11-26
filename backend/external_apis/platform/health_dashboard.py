"""Aggregated health dashboard for every integration."""
from __future__ import annotations

from ..health import health_dashboard


async def dashboard():
    return await health_dashboard()

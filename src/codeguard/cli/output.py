"""Backwards-compat shim — renderers now live in `cli/render/`."""

from .render import (
    render_alerts_view,
    render_baseline_already_exists,
    render_baseline_created,
    render_history,
    render_review_summary,
    render_scan_no_baseline,
    render_scan_not_found,
    render_scan_result,
    render_status,
)

__all__ = [
    "render_alerts_view",
    "render_baseline_already_exists",
    "render_baseline_created",
    "render_history",
    "render_review_summary",
    "render_scan_no_baseline",
    "render_scan_not_found",
    "render_scan_result",
    "render_status",
]

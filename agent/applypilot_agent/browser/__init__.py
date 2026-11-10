"""Playwright browser automation and URL security package."""

from applypilot_agent.browser.form_inspector import inspect_form_dom
from applypilot_agent.browser.url_security import UnsafeURLError, ValidatedTarget, validate_target_url
from applypilot_agent.browser.worker import (
    DraftFillResult,
    PlaywrightDraftWorker,
    SubmissionResult,
    compute_form_structure_hash,
)

__all__ = [
    "DraftFillResult",
    "PlaywrightDraftWorker",
    "SubmissionResult",
    "UnsafeURLError",
    "ValidatedTarget",
    "compute_form_structure_hash",
    "inspect_form_dom",
    "validate_target_url",
]

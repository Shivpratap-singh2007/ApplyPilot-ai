"""Playwright browser automation worker for safe form inspection, draft filling, and approved submission."""

import hashlib
import json
from pathlib import Path
import re
import threading
from typing import Any, Literal

from playwright.sync_api import Browser, Page, Route, sync_playwright
from pydantic import BaseModel, Field

from applypilot_agent.ai.provider import AIProvider, analyze_fields_hybrid
from applypilot_agent.ai.schemas import FieldMatchResult, FormFieldDescriptor, ProfileContext
from applypilot_agent.browser.form_inspector import inspect_form_dom
from applypilot_agent.browser.url_security import UnsafeURLError, validate_target_url

_CONFIRM_REF_RE = re.compile(r"\b(?:ref(?:erence)?|id|confirmation)\s*[:#]\s*([A-Z0-9][A-Z0-9_-]{3,40})", re.IGNORECASE)
_CONFIRM_PHRASES = (
    "application confirmed",
    "application submitted",
    "thank you for applying",
    "successfully submitted",
    "registration confirmed",
    "submission received",
    "we have received your application",
)


def compute_form_structure_hash(target_url: str, fields: list[FormFieldDescriptor]) -> str:
    """Compute a deterministic SHA-256 hash of target URL and material form structure."""
    normalized = [
        {
            "field_id": f.field_id,
            "tag": f.tag,
            "input_type": f.input_type,
            "name": f.name,
            "element_id": f.element_id,
            "required": f.required,
            "selector": f.selector,
            "options": f.options,
        }
        for f in sorted(fields, key=lambda item: item.field_id)
    ]
    payload = json.dumps({"target_url": target_url, "fields": normalized}, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class DraftFillResult(BaseModel):
    """Structured outcome of inspecting and filling a draft application without submitting."""

    status: Literal["WAITING_FOR_REVIEW", "WAITING_FOR_USER_INPUT", "FAILED"]
    url: str
    page_title: str = ""
    heading: str = ""
    submitted: bool = False
    is_multi_step: bool = False
    steps_inspected: int = 1
    form_structure_hash: str = ""
    challenge_reason: str | None = None
    fields: list[FormFieldDescriptor] = Field(default_factory=list)
    matches: list[FieldMatchResult] = Field(default_factory=list)
    filled_field_ids: list[str] = Field(default_factory=list)
    missing_required_fields: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    screenshot_path: str | None = None
    ai_provider_used: str = "deterministic_only"
    ai_warnings: list[str] = Field(default_factory=list)


class SubmissionResult(BaseModel):
    """Structured outcome of executing an explicitly approved submission."""

    status: Literal["SUBMITTED", "FAILED", "UNKNOWN", "WAITING_FOR_USER_INPUT", "REQUIRES_NEW_REVIEW"]
    url: str
    confirmation_reference: str | None = None
    confirmation_evidence: dict[str, Any] = Field(default_factory=dict)
    validation_errors: list[str] = Field(default_factory=list)
    error_message: str | None = None
    screenshot_path: str | None = None


class PlaywrightDraftWorker:
    """
    Isolated Playwright worker for safe form inspection, draft filling, and approved submission.

    Concurrency is bounded to protect memory on 16 GB Windows laptops.
    """

    def __init__(
        self,
        *,
        headless: bool = True,
        timeout_ms: int = 20000,
        max_concurrent_contexts: int = 2,
        browser_channel: str | None = None,
    ) -> None:
        self.headless = headless
        self.timeout_ms = timeout_ms
        self._semaphore = threading.Semaphore(max(1, max_concurrent_contexts))
        self.browser_channel = browser_channel

    def _launch_browser(self, pw) -> Browser:
        """Launch Playwright Chromium, falling back to local Chrome or Edge if needed."""
        launch_args = ["--disable-dev-shm-usage"]
        if self.browser_channel:
            return pw.chromium.launch(headless=self.headless, channel=self.browser_channel, args=launch_args)

        try:
            return pw.chromium.launch(headless=self.headless, args=launch_args)
        except Exception:
            for fallback_channel in ("chrome", "msedge"):
                try:
                    return pw.chromium.launch(headless=self.headless, channel=fallback_channel, args=launch_args)
                except Exception:
                    continue
            raise

    def _wait_for_dynamic_fields(self, page: Page) -> None:
        """Allow short dynamic JS hydration to render async form fields cleanly."""
        try:
            page.wait_for_selector("form input, form textarea, form select", timeout=2000)
        except Exception:
            pass
        page.wait_for_timeout(350)

    def _fill_single_field(self, page: Page, field: FormFieldDescriptor, value: str) -> bool:
        """Fill a single form control using resilient accessible/attribute locators."""
        if not value:
            return False

        if field.tag == "checkbox":
            locator = page.locator(field.selector).first if field.selector else page.get_by_label(field.label).first
            if locator.count() == 0:
                return False
            if value.lower() in {"true", "yes", "1", "checked"}:
                locator.check()
            else:
                locator.uncheck()
            return True

        if field.tag == "radio_group":
            if field.name:
                scoped_label = page.locator(
                    f'label:has(input[type="radio"][name="{field.name}"])',
                    has_text=value,
                ).first
                if scoped_label.count() > 0:
                    scoped_label.click()
                    return True
                by_value = page.locator(f'input[type="radio"][name="{field.name}"][value="{value}"]').first
                if by_value.count() > 0:
                    by_value.check()
                    return True
            return False

        locator = None
        if field.selector:
            locator = page.locator(field.selector).first
        elif field.label:
            locator = page.get_by_label(field.label, exact=False).first
        elif field.placeholder:
            locator = page.get_by_placeholder(field.placeholder, exact=False).first

        if locator is None or locator.count() == 0:
            return False

        if field.input_type == "file":
            file_path = Path(value)
            if not file_path.is_file():
                return False
            locator.set_input_files(str(file_path))
            return True

        if field.tag == "select":
            try:
                locator.select_option(label=value)
            except Exception:
                locator.select_option(value=value)
            return True

        locator.fill(value)
        return True

    def _click_next_step_if_present(self, page: Page) -> bool:
        """Advance an explicit non-submit multi-step Next/Continue button when present."""
        candidates = (
            page.locator('button[data-step-next="true"]:visible').first,
            page.locator('button[type="button"]:visible', has_text=re.compile(r"^(next|next step|continue)$", re.I)).first,
        )
        for btn in candidates:
            if btn.count() > 0 and btn.is_enabled():
                btn.click()
                page.wait_for_timeout(200)
                return True
        return False

    def inspect_and_fill_draft(
        self,
        *,
        url: str,
        profile: ProfileContext,
        ai_provider: AIProvider | None = None,
        screenshot_path: Path | None = None,
        allow_localhost: bool = False,
    ) -> DraftFillResult:
        """
        Validate URL, inspect form (including bounded multi-step progression),
        match fields, fill draft values WITHOUT submitting, and capture screenshot evidence.
        """
        validated = validate_target_url(url, allow_localhost=allow_localhost)

        with self._semaphore:
            with sync_playwright() as pw:
                browser = self._launch_browser(pw)
                context = browser.new_context(accept_downloads=False)
                context.set_default_timeout(self.timeout_ms)

                def _guard_navigation(route: Route) -> None:
                    req = route.request
                    if req.resource_type == "document":
                        try:
                            validate_target_url(req.url, allow_localhost=allow_localhost)
                        except UnsafeURLError:
                            route.abort()
                            return
                    route.continue_()

                context.route("**/*", _guard_navigation)

                try:
                    page = context.new_page()
                    page.goto(validated.url, wait_until="domcontentloaded")
                    page.wait_for_load_state("networkidle")
                    self._wait_for_dynamic_fields(page)

                    all_fields_by_id: dict[str, FormFieldDescriptor] = {}
                    all_matches_by_id: dict[str, FieldMatchResult] = {}
                    filled_ids: list[str] = []
                    missing_required: list[str] = []
                    ai_warnings: list[str] = []
                    provider_used = "deterministic_only"
                    steps_inspected = 0
                    is_multi_step = False
                    last_dom: dict[str, Any] = {}

                    for step_idx in range(5):
                        steps_inspected = step_idx + 1
                        dom_info = inspect_form_dom(page)
                        last_dom = dom_info

                        if dom_info["has_captcha_or_challenge"]:
                            saved_shot = None
                            if screenshot_path is not None:
                                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                                page.screenshot(path=str(screenshot_path), full_page=True)
                                saved_shot = str(screenshot_path)
                            return DraftFillResult(
                                status="WAITING_FOR_USER_INPUT",
                                url=page.url,
                                page_title=dom_info["page_title"],
                                heading=dom_info.get("heading", ""),
                                submitted=False,
                                is_multi_step=is_multi_step,
                                steps_inspected=steps_inspected,
                                form_structure_hash=compute_form_structure_hash(
                                    validated.url, list(all_fields_by_id.values()) or dom_info["fields"]
                                ),
                                challenge_reason=dom_info["challenge_reason"],
                                fields=list(all_fields_by_id.values()) or dom_info["fields"],
                                matches=list(all_matches_by_id.values()),
                                validation_errors=dom_info["validation_errors"],
                                screenshot_path=saved_shot,
                            )

                        step_fields: list[FormFieldDescriptor] = dom_info["fields"]
                        new_fields = [f for f in step_fields if f.field_id not in all_fields_by_id]
                        for f in step_fields:
                            all_fields_by_id[f.field_id] = f

                        if new_fields:
                            step_matches, step_provider, step_warnings = analyze_fields_hybrid(
                                fields=new_fields,
                                profile=profile,
                                ai_provider=ai_provider,
                            )
                            if step_provider != "deterministic_only":
                                provider_used = step_provider
                            ai_warnings.extend(step_warnings)
                            for m in step_matches:
                                all_matches_by_id[m.field_id] = m

                        for f in step_fields:
                            match = all_matches_by_id.get(f.field_id)
                            if match is None or not match.proposed_value:
                                label_name = f.label or f.name or f.field_id
                                if f.required and label_name not in missing_required:
                                    missing_required.append(label_name)
                                continue
                            if self._fill_single_field(page, f, match.proposed_value):
                                if f.field_id not in filled_ids:
                                    filled_ids.append(f.field_id)

                        if dom_info.get("has_next_step_button") and self._click_next_step_if_present(page):
                            is_multi_step = True
                            continue
                        break

                    saved_shot = None
                    if screenshot_path is not None:
                        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(screenshot_path), full_page=True)
                        saved_shot = str(screenshot_path)

                    post_dom = inspect_form_dom(page)
                    all_fields = list(all_fields_by_id.values())
                    return DraftFillResult(
                        status="WAITING_FOR_USER_INPUT" if missing_required else "WAITING_FOR_REVIEW",
                        url=page.url,
                        page_title=last_dom.get("page_title", ""),
                        heading=last_dom.get("heading", ""),
                        submitted=False,
                        is_multi_step=is_multi_step,
                        steps_inspected=steps_inspected,
                        form_structure_hash=compute_form_structure_hash(validated.url, all_fields),
                        fields=all_fields,
                        matches=list(all_matches_by_id.values()),
                        filled_field_ids=filled_ids,
                        missing_required_fields=missing_required,
                        validation_errors=post_dom["validation_errors"],
                        screenshot_path=saved_shot,
                        ai_provider_used=provider_used,
                        ai_warnings=ai_warnings,
                    )
                finally:
                    context.close()
                    browser.close()

    def submit_approved_application(
        self,
        *,
        url: str,
        approved_values: dict[str, str],
        expected_form_structure_hash: str,
        resume_file_path: str | None = None,
        screenshot_path: Path | None = None,
        allow_localhost: bool = False,
    ) -> SubmissionResult:
        """
        Re-verify target URL and form structure against the immutable approval snapshot,
        fill the approved values, click Submit, and verify confirmation evidence.
        """
        validated = validate_target_url(url, allow_localhost=allow_localhost)

        with self._semaphore:
            with sync_playwright() as pw:
                browser = self._launch_browser(pw)
                context = browser.new_context(accept_downloads=False)
                context.set_default_timeout(self.timeout_ms)

                def _guard_navigation(route: Route) -> None:
                    req = route.request
                    if req.resource_type == "document":
                        try:
                            validate_target_url(req.url, allow_localhost=allow_localhost)
                        except UnsafeURLError:
                            route.abort()
                            return
                    route.continue_()

                context.route("**/*", _guard_navigation)

                try:
                    page = context.new_page()
                    page.goto(validated.url, wait_until="domcontentloaded")
                    page.wait_for_load_state("networkidle")
                    self._wait_for_dynamic_fields(page)

                    observed_fields_by_id: dict[str, FormFieldDescriptor] = {}

                    for _step in range(5):
                        dom_info = inspect_form_dom(page)
                        if dom_info["has_captcha_or_challenge"]:
                            return SubmissionResult(
                                status="WAITING_FOR_USER_INPUT",
                                url=page.url,
                                error_message=dom_info["challenge_reason"],
                            )

                        for field in dom_info["fields"]:
                            observed_fields_by_id[field.field_id] = field
                            val = approved_values.get(field.field_id, "")
                            if field.input_type == "file" and resume_file_path:
                                val = resume_file_path
                            if val:
                                self._fill_single_field(page, field, val)

                        if dom_info.get("has_next_step_button") and self._click_next_step_if_present(page):
                            continue
                        break

                    current_hash = compute_form_structure_hash(
                        validated.url, list(observed_fields_by_id.values())
                    )
                    if expected_form_structure_hash and current_hash != expected_form_structure_hash:
                        return SubmissionResult(
                            status="REQUIRES_NEW_REVIEW",
                            url=page.url,
                            error_message=(
                                "Target form structure changed after approval; "
                                "submission aborted and a fresh review is required."
                            ),
                        )

                    submit_btn = page.locator(
                        'button[type="submit"]:visible, input[type="submit"]:visible'
                    ).first
                    if submit_btn.count() == 0:
                        submit_btn = page.locator(
                            'button:visible',
                            has_text=re.compile(r"(submit|apply|complete|send application)", re.I),
                        ).first

                    if submit_btn.count() == 0:
                        return SubmissionResult(
                            status="FAILED",
                            url=page.url,
                            error_message="No visible Submit button found on the application form.",
                        )

                    pre_submit_url = page.url
                    response_status: int | None = None
                    try:
                        with page.expect_response(lambda r: r.request.resource_type in {"document", "xhr", "fetch"}, timeout=6000) as resp_info:
                            submit_btn.click()
                        response_status = resp_info.value.status
                    except Exception:
                        # Either client-side JS prevented submission due to validation or server timed out.
                        pass

                    page.wait_for_timeout(400)
                    post_dom = inspect_form_dom(page)

                    saved_shot = None
                    if screenshot_path is not None:
                        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(screenshot_path), full_page=True)
                        saved_shot = str(screenshot_path)

                    validation_errors = list(post_dom.get("validation_errors", []))
                    # Also check HTML5 invalid inputs still sitting on the page
                    invalid_count = page.locator("input:invalid, select:invalid, textarea:invalid").count()
                    if invalid_count > 0 and not validation_errors:
                        validation_errors.append(
                            f"{invalid_count} required or constrained field(s) failed browser validation."
                        )

                    body_text = str(post_dom.get("body_text", ""))
                    body_lower = body_text.lower()

                    if validation_errors or (response_status is not None and response_status >= 400):
                        return SubmissionResult(
                            status="FAILED",
                            url=page.url,
                            validation_errors=validation_errors,
                            error_message="; ".join(validation_errors)
                            or f"Server returned HTTP {response_status} during submission.",
                            screenshot_path=saved_shot,
                        )

                    ref_match = _CONFIRM_REF_RE.search(body_text)
                    has_phrase = any(phrase in body_lower for phrase in _CONFIRM_PHRASES)

                    if has_phrase or ref_match:
                        return SubmissionResult(
                            status="SUBMITTED",
                            url=page.url,
                            confirmation_reference=ref_match.group(1) if ref_match else None,
                            confirmation_evidence={
                                "final_url": page.url,
                                "previous_url": pre_submit_url,
                                "http_status": response_status,
                                "matched_phrase": next((p for p in _CONFIRM_PHRASES if p in body_lower), None),
                                "page_title": post_dom.get("page_title", ""),
                                "snippet": body_text[:400],
                            },
                            screenshot_path=saved_shot,
                        )

                    # No explicit validation errors, but no clear confirmation evidence either -> UNKNOWN
                    return SubmissionResult(
                        status="UNKNOWN",
                        url=page.url,
                        confirmation_evidence={
                            "final_url": page.url,
                            "previous_url": pre_submit_url,
                            "http_status": response_status,
                            "snippet": body_text[:400],
                        },
                        error_message=(
                            "Submission was triggered, but no unambiguous confirmation evidence was detected. "
                            "Do not automatically retry before checking your email or portal."
                        ),
                        screenshot_path=saved_shot,
                    )
                finally:
                    context.close()
                    browser.close()

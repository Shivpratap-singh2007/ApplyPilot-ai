"""DOM-based form field, challenge, multi-step, and validation error extraction using Playwright."""

from typing import Any

from playwright.sync_api import Page

from applypilot_agent.ai.schemas import FormFieldDescriptor

_DOM_INSPECT_SCRIPT = r"""
() => {
  const isVisible = (el) => {
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || el.disabled) {
      return false;
    }
    const rect = el.getBoundingClientRect();
    return rect.width > 0 || rect.height > 0 || el.type === 'file';
  };

  const cleanText = (txt) => (txt || '').replace(/\s+/g, ' ').trim();

  const labelFor = (el) => {
    const aria = el.getAttribute('aria-label');
    if (aria) return cleanText(aria);
    const labelledBy = el.getAttribute('aria-labelledby');
    if (labelledBy) {
      const parts = labelledBy.split(/\s+/).map(id => document.getElementById(id)?.innerText || '');
      const joined = cleanText(parts.join(' '));
      if (joined) return joined;
    }
    if (el.id) {
      const explicit = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (explicit) return cleanText(explicit.innerText);
    }
    const parentLabel = el.closest('label');
    if (parentLabel) {
      const clone = parentLabel.cloneNode(true);
      clone.querySelectorAll('input,select,textarea').forEach(n => n.remove());
      const txt = cleanText(clone.innerText);
      if (txt) return txt;
    }
    const fieldWrap = el.closest('.field, .form-group, .form-field, div, p');
    if (fieldWrap) {
      const lbl = fieldWrap.querySelector('label, legend, .label');
      if (lbl) return cleanText(lbl.innerText);
    }
    return '';
  };

  const nearbyTextFor = (el) => {
    const container = el.closest('.field, .form-group, .form-field, fieldset, div');
    if (!container) return '';
    const clone = container.cloneNode(true);
    clone.querySelectorAll('input,select,textarea').forEach(n => n.remove());
    return cleanText(clone.innerText).slice(0, 220);
  };

  const buildSelector = (el) => {
    if (el.id) return `#${CSS.escape(el.id)}`;
    if (el.name) return `${el.tagName.toLowerCase()}[name="${CSS.escape(el.name)}"]`;
    return '';
  };

  const fields = [];
  const radioGroups = new Map();
  let counter = 0;

  const elements = document.querySelectorAll('input, textarea, select');
  for (const el of elements) {
    const tag = el.tagName.toLowerCase();
    const inputType = tag === 'input' ? (el.getAttribute('type') || 'text').toLowerCase() : tag;
    if (['hidden', 'submit', 'button', 'reset', 'image'].includes(inputType)) {
      continue;
    }
    if (!isVisible(el)) {
      continue;
    }

    if (inputType === 'radio') {
      const groupName = el.name || `radio_${counter}`;
      if (!radioGroups.has(groupName)) {
        const fieldset = el.closest('fieldset');
        const legend = fieldset ? cleanText(fieldset.querySelector('legend')?.innerText || '') : '';
        radioGroups.set(groupName, {
          field_id: el.name || `field_${counter++}`,
          tag: 'radio_group',
          input_type: 'radio',
          name: el.name || '',
          element_id: '',
          label: legend || labelFor(el),
          placeholder: '',
          nearby_text: nearbyTextFor(el),
          required: Boolean(el.required || el.getAttribute('aria-required') === 'true'),
          options: [],
          selector: el.name ? `input[type="radio"][name="${CSS.escape(el.name)}"]` : buildSelector(el),
          current_value: '',
        });
      }
      const group = radioGroups.get(groupName);
      const optLabel = labelFor(el) || el.value || '';
      if (optLabel && !group.options.includes(optLabel)) {
        group.options.push(optLabel);
      }
      if (el.checked) {
        group.current_value = optLabel || el.value;
      }
      continue;
    }

    const options = tag === 'select'
      ? Array.from(el.options).map(o => cleanText(o.text || o.value)).filter(Boolean)
      : [];

    const label = labelFor(el);
    fields.push({
      field_id: el.id || el.name || `field_${counter}`,
      tag: inputType === 'checkbox' ? 'checkbox' : tag,
      input_type: inputType,
      name: el.name || '',
      element_id: el.id || '',
      label: label,
      placeholder: cleanText(el.getAttribute('placeholder') || ''),
      nearby_text: nearbyTextFor(el),
      required: Boolean(el.required || el.getAttribute('aria-required') === 'true' || label.includes('*')),
      options,
      selector: buildSelector(el),
      current_value: inputType === 'checkbox' ? String(Boolean(el.checked)) : String(el.value || ''),
    });
    counter += 1;
  }

  for (const group of radioGroups.values()) {
    fields.push(group);
  }

  let challengeReason = null;
  if (document.querySelector('iframe[src*="recaptcha"], iframe[src*="hcaptcha"], .cf-turnstile, [data-applypilot-captcha="true"]')) {
    challengeReason = 'CAPTCHA or bot-verification challenge detected on page.';
  } else {
    const bodyText = cleanText(document.body?.innerText || '').toLowerCase();
    if (bodyText.includes('verify you are human') || bodyText.includes('one-time passcode')) {
      challengeReason = 'Human verification or OTP prompt detected on page.';
    }
  }

  const validationErrors = Array.from(
    document.querySelectorAll('[role="alert"], .error-message, .invalid-feedback')
  )
    .filter(el => isVisible(el))
    .map(el => cleanText(el.innerText))
    .filter(Boolean);

  const hasNextStepButton = Array.from(document.querySelectorAll('button, input[type="button"]'))
    .filter(el => isVisible(el))
    .some(el => {
      if (el.dataset && el.dataset.stepNext === 'true') return true;
      const label = cleanText(el.innerText || el.value || '').toLowerCase();
      return (label === 'next' || label === 'next step' || label === 'continue') && el.type !== 'submit';
    });

  const heading = cleanText(document.querySelector('h1')?.innerText || '');

  return {
    page_title: document.title || '',
    heading,
    body_text: cleanText(document.body?.innerText || '').slice(0, 2000),
    fields,
    has_captcha_or_challenge: Boolean(challengeReason),
    challenge_reason: challengeReason,
    validation_errors: validationErrors,
    has_next_step_button: hasNextStepButton,
  };
}
"""


def inspect_form_dom(page: Page) -> dict[str, Any]:
    """Inspect active form controls, multi-step cues, CAPTCHA challenges, and validation errors."""
    raw = page.evaluate(_DOM_INSPECT_SCRIPT)
    descriptors = [FormFieldDescriptor.model_validate(item) for item in raw.get("fields", [])]
    return {
        "page_title": str(raw.get("page_title", "")),
        "heading": str(raw.get("heading", "")),
        "body_text": str(raw.get("body_text", "")),
        "fields": descriptors,
        "has_captcha_or_challenge": bool(raw.get("has_captcha_or_challenge", False)),
        "challenge_reason": raw.get("challenge_reason"),
        "validation_errors": [str(e) for e in raw.get("validation_errors", [])],
        "has_next_step_button": bool(raw.get("has_next_step_button", False)),
    }

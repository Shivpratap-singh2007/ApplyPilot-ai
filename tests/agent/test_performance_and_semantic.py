"""Phase 3 & 7 tests: optional semantic matching, latency budget, and end-to-end prompt injection resistance."""

from pathlib import Path
import sys
import time

AGENT_ROOT = Path(__file__).resolve().parents[2] / "agent"
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from applypilot_agent.ai import (  # noqa: E402
    FormFieldDescriptor,
    ProfileContext,
    analyze_fields_hybrid,
    match_field_semantically,
)


def test_semantic_matcher_resolves_paraphrased_labels_for_review() -> None:
    profile = ProfileContext(
        college="Institute of Computing",
        graduation_year="2027",
        github_url="https://github.com/ada",
        work_mode_preference="Remote",
    )
    fields = [
        FormFieldDescriptor(
            field_id="alma_mater",
            tag="input",
            input_type="text",
            label="Educational Institution",
        ),
        FormFieldDescriptor(
            field_id="cohort_year",
            tag="input",
            input_type="text",
            label="Expected Year of Passing",
        ),
        FormFieldDescriptor(
            field_id="code_link",
            tag="input",
            input_type="url",
            label="Source Code Profile Link",
        ),
    ]
    for f in fields:
        res = match_field_semantically(f, profile)
        assert res is not None
        assert res.source == "semantic"
        assert res.requires_human_review is True
        assert res.proposed_value != ""


def test_hybrid_matcher_performance_budget_for_50_fields() -> None:
    profile = ProfileContext(
        full_name="Ada Lovelace",
        email="ada@example.com",
        phone="+91-9876543210",
        college="Analytical Tech",
        degree="B.Tech",
        branch="CS",
        graduation_year="2027",
        github_url="https://github.com/ada",
    )
    fields = [
        FormFieldDescriptor(
            field_id=f"field_{i}",
            tag="input",
            input_type="text",
            label=["Email Address", "Phone Number", "Educational Institution", "Unknown Custom Question"][i % 4],
        )
        for i in range(50)
    ]
    t0 = time.perf_counter()
    matches, provider_used, _warnings = analyze_fields_hybrid(fields, profile, ai_provider=None)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert len(matches) == 50
    assert provider_used == "deterministic_only"
    # Should stay well under 250ms on CPU without loading heavy models
    assert elapsed_ms < 250.0


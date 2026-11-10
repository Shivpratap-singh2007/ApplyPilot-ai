"""Resume upload validation, secure storage, text extraction, and user-verified mapping."""

import hashlib
from io import BytesIO
from pathlib import Path
import re
import uuid

from docx import Document as DocxDocument
from fastapi import UploadFile
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.crypto import decrypt_text, encrypt_text
from app.models.resume import Resume
from app.models.user import User
from app.services.audit_service import record_audit_event
from app.services.profile_service import get_or_create_profile

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3,5}\)?[\s-]?)?\d{3,5}[\s-]?\d{4}")
_GITHUB_RE = re.compile(r"https?://(?:www\.)?github\.com/[A-Za-z0-9_-]+", re.IGNORECASE)
_LINKEDIN_RE = re.compile(r"https?://(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+", re.IGNORECASE)
_GRAD_YEAR_RE = re.compile(r"\b(202[4-9]|203[0-5])\b")
_CGPA_RE = re.compile(r"\b(?:CGPA|GPA)\s*[:\-]?\s*(\d(?:\.\d{1,2})?(?:\s*/\s*(?:10|4(?:\.0)?))?)", re.IGNORECASE)

_KNOWN_LANGS = (
    "Python",
    "TypeScript",
    "JavaScript",
    "Java",
    "C++",
    "C",
    "Go",
    "Rust",
    "SQL",
)
_KNOWN_SKILLS = (
    "FastAPI",
    "Next.js",
    "React",
    "Tailwind CSS",
    "Docker",
    "Git",
    "PostgreSQL",
    "SQLite",
    "Playwright",
    "Linux",
    "Node.js",
    "REST APIs",
    "Machine Learning",
)
_KNOWN_DEGREES = ("B.Tech", "B.E", "B.Sc", "M.Tech", "M.Sc", "MCA", "BCA", "B.A", "MBA")


class ResumeValidationError(ValueError):
    """Raised when an uploaded file fails extension, signature, or size checks."""


class ResumeNotFoundError(LookupError):
    """Raised when a resume does not exist or is not owned by the user."""


def _extract_text_from_bytes(ext: str, content: bytes) -> str:
    if ext == "pdf":
        reader = PdfReader(BytesIO(content))
        parts = [(page.extract_text() or "").strip() for page in reader.pages[:20]]
        return "\n".join(p for p in parts if p).strip()
    if ext == "docx":
        doc = DocxDocument(BytesIO(content))
        parts = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
        return "\n".join(parts).strip()
    return ""


def _extract_structured_resume_hints(text: str) -> dict[str, object]:
    """Deterministically extract verifiable candidate fields from resume text."""
    hints: dict[str, object] = {}
    if not text:
        return hints

    email_m = _EMAIL_RE.search(text)
    if email_m:
        hints["email"] = email_m.group(0)

    phone_m = _PHONE_RE.search(text)
    if phone_m:
        hints["phone"] = phone_m.group(0).strip()

    gh_m = _GITHUB_RE.search(text)
    if gh_m:
        hints["github_url"] = gh_m.group(0)

    li_m = _LINKEDIN_RE.search(text)
    if li_m:
        hints["linkedin_url"] = li_m.group(0)

    cgpa_m = _CGPA_RE.search(text)
    if cgpa_m:
        hints["cgpa"] = cgpa_m.group(1)

    year_m = _GRAD_YEAR_RE.search(text)
    if year_m:
        hints["graduation_year"] = year_m.group(1)

    lowered = text.lower()
    for deg in _KNOWN_DEGREES:
        if re.search(rf"\b{re.escape(deg.lower())}\b", lowered):
            hints["degree"] = deg
            break

    found_langs = [
        lang for lang in _KNOWN_LANGS
        if re.search(rf"(?<!\w){re.escape(lang.lower())}(?!\w)", lowered)
    ]
    if found_langs:
        hints["programming_languages"] = found_langs

    found_skills = [
        skill for skill in _KNOWN_SKILLS
        if re.search(rf"(?<!\w){re.escape(skill.lower())}(?!\w)", lowered)
    ]
    if found_skills:
        hints["technical_skills"] = found_skills

    return hints


def upload_resume(
    db: Session,
    user: User,
    upload: UploadFile,
    *,
    label: str | None = None,
    ip_address: str | None = None,
) -> Resume:
    """Validate, persist, and extract text/hints from an uploaded PDF or DOCX resume."""
    settings = get_settings()
    raw_name = Path(upload.filename or "resume").name
    ext = Path(raw_name).suffix.lower().lstrip(".")
    if ext not in {"pdf", "docx"}:
        raise ResumeValidationError("Only .pdf and .docx resume files are supported.")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = upload.file.read(max_bytes + 1)
    if not content:
        raise ResumeValidationError("Uploaded resume file is empty.")
    if len(content) > max_bytes:
        raise ResumeValidationError(f"Resume exceeds maximum allowed size of {settings.max_upload_mb} MB.")

    if ext == "pdf" and not content.startswith(b"%PDF-"):
        raise ResumeValidationError("File extension is .pdf, but file header is not a valid PDF signature.")
    if ext == "docx" and not content.startswith(b"PK\x03\x04"):
        raise ResumeValidationError("File extension is .docx, but file header is not a valid DOCX archive.")

    try:
        extracted_text = _extract_text_from_bytes(ext, content)
    except Exception as exc:
        raise ResumeValidationError(f"Could not parse {ext.upper()} resume safely: {type(exc).__name__}") from exc

    extracted_hints = _extract_structured_resume_hints(extracted_text)
    sha256 = hashlib.sha256(content).hexdigest()

    user_upload_dir = settings.upload_dir / user.id
    user_upload_dir.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid.uuid4()}.{ext}"
    abs_target = (user_upload_dir / stored_filename).resolve()
    if user_upload_dir.resolve() not in abs_target.parents:
        raise ResumeValidationError("Invalid storage target path.")
    abs_target.write_bytes(content)

    existing_count = len(list(db.scalars(select(Resume.id).where(Resume.user_id == user.id))))
    is_first = existing_count == 0
    clean_label = (label or Path(raw_name).stem or "Primary Resume").strip()[:160]

    resume = Resume(
        user_id=user.id,
        label=clean_label,
        original_filename=raw_name[:255],
        stored_rel_path=f"{user.id}/{stored_filename}",
        content_type=upload.content_type or ("application/pdf" if ext == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        file_size_bytes=len(content),
        sha256_hash=sha256,
        extracted_text=encrypt_text(extracted_text[:40000]),
        extracted_data_json=extracted_hints,
        is_verified=False,
        is_preferred=is_first,
    )
    db.add(resume)
    db.flush()

    if is_first:
        profile = get_or_create_profile(db, user)
        profile.preferred_resume_id = resume.id
        db.add(profile)

    record_audit_event(
        db,
        event_type="resume.uploaded",
        user_id=user.id,
        resource_type="resume",
        resource_id=resume.id,
        ip_address=ip_address,
        details={"filename": resume.original_filename, "sha256": sha256},
        commit=False,
    )
    db.commit()
    db.refresh(resume)
    return resume


def serialize_resume(resume: Resume) -> dict[str, object]:
    """Serialize a Resume ORM model with decrypted extracted text for its owner."""
    return {
        "id": resume.id,
        "user_id": resume.user_id,
        "label": resume.label,
        "original_filename": resume.original_filename,
        "content_type": resume.content_type,
        "file_size_bytes": resume.file_size_bytes,
        "sha256_hash": resume.sha256_hash,
        "extracted_text": decrypt_text(resume.extracted_text),
        "extracted_data_json": resume.extracted_data_json,
        "is_verified": resume.is_verified,
        "is_preferred": resume.is_preferred,
        "created_at": resume.created_at,
    }


def list_user_resumes(db: Session, user: User) -> list[Resume]:
    """List all resumes owned by the authenticated user."""
    return list(
        db.scalars(
            select(Resume).where(Resume.user_id == user.id).order_by(Resume.is_preferred.desc(), Resume.created_at.desc())
        )
    )


def get_user_resume_or_raise(db: Session, user: User, resume_id: str) -> Resume:
    """Fetch a resume strictly owned by the user or raise ResumeNotFoundError."""
    resume = db.scalar(select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id))
    if resume is None:
        raise ResumeNotFoundError("Resume not found.")
    return resume


def resolve_resume_abs_path(resume: Resume) -> Path:
    """Safely resolve a stored resume path inside UPLOAD_DIR."""
    settings = get_settings()
    base = settings.upload_dir.resolve()
    target = (base / resume.stored_rel_path).resolve()
    if base not in target.parents:
        raise ResumeValidationError("Stored resume path escapes upload sandbox.")
    return target


def set_preferred_resume(
    db: Session,
    user: User,
    resume_id: str,
    *,
    ip_address: str | None = None,
) -> Resume:
    """Mark one resume as preferred and update UserProfile.preferred_resume_id."""
    target = get_user_resume_or_raise(db, user, resume_id)
    for item in list_user_resumes(db, user):
        item.is_preferred = item.id == target.id
        db.add(item)

    profile = get_or_create_profile(db, user)
    profile.preferred_resume_id = target.id
    db.add(profile)
    record_audit_event(
        db,
        event_type="resume.preferred",
        user_id=user.id,
        resource_type="resume",
        resource_id=target.id,
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(target)
    return target


def apply_extracted_to_profile(
    db: Session,
    user: User,
    resume_id: str,
    fields_to_apply: list[str],
    mark_as_verified: bool,
    *,
    ip_address: str | None = None,
):
    """Copy user-approved extracted resume hints into the user's profile."""
    resume = get_user_resume_or_raise(db, user, resume_id)
    profile = get_or_create_profile(db, user)
    hints = resume.extracted_data_json or {}
    verified_map = dict(profile.verified_fields or {})

    allowed_apply_keys = {
        "email",
        "phone",
        "github_url",
        "linkedin_url",
        "cgpa",
        "graduation_year",
        "degree",
        "programming_languages",
        "technical_skills",
    }
    target_keys = fields_to_apply or [k for k in hints.keys() if k in allowed_apply_keys]
    applied: list[str] = []

    for key in target_keys:
        if key in allowed_apply_keys and key in hints:
            setattr(profile, key, hints[key])
            verified_map[key] = bool(mark_as_verified)
            applied.append(key)

    profile.verified_fields = verified_map
    if mark_as_verified:
        resume.is_verified = True
        db.add(resume)

    db.add(profile)
    record_audit_event(
        db,
        event_type="resume.extracted_applied",
        user_id=user.id,
        resource_type="resume",
        resource_id=resume.id,
        ip_address=ip_address,
        details={"applied_fields": applied, "verified": mark_as_verified},
        commit=False,
    )
    db.commit()
    db.refresh(profile)
    return profile


def delete_resume(
    db: Session,
    user: User,
    resume_id: str,
    *,
    ip_address: str | None = None,
) -> None:
    """Delete a user's resume record and remove its file from local storage."""
    resume = get_user_resume_or_raise(db, user, resume_id)
    abs_path = resolve_resume_abs_path(resume)

    profile = get_or_create_profile(db, user)
    if profile.preferred_resume_id == resume.id:
        profile.preferred_resume_id = None
        db.add(profile)

    db.delete(resume)
    record_audit_event(
        db,
        event_type="resume.deleted",
        user_id=user.id,
        resource_type="resume",
        resource_id=resume_id,
        ip_address=ip_address,
        commit=False,
    )
    db.commit()

    if abs_path.is_file():
        abs_path.unlink(missing_ok=True)


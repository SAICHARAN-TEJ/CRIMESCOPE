"""CrimeScope case and report persistence models."""

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from ..config import Config


@dataclass
class CrimeScopeCase:
    """CrimeScope case object."""

    case_id: str
    title: str
    investigative_question: str
    seed_packet: Dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    latest_report_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "title": self.title,
            "investigative_question": self.investigative_question,
            "seed_packet": self.seed_packet,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "latest_report_id": self.latest_report_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CrimeScopeCase":
        return cls(
            case_id=data["case_id"],
            title=data.get("title", "Untitled Case"),
            investigative_question=data.get("investigative_question", ""),
            seed_packet=data.get("seed_packet", {}),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            latest_report_id=data.get("latest_report_id"),
        )


class CrimeScopeCaseManager:
    """CrimeScope case storage manager."""

    CASES_DIR = os.path.join(Config.UPLOAD_FOLDER, "crimescope", "cases")

    @classmethod
    def _ensure_cases_dir(cls) -> None:
        os.makedirs(cls.CASES_DIR, exist_ok=True)

    @classmethod
    def _get_case_dir(cls, case_id: str) -> str:
        return os.path.join(cls.CASES_DIR, case_id)

    @classmethod
    def _get_case_meta_path(cls, case_id: str) -> str:
        return os.path.join(cls._get_case_dir(case_id), "case.json")

    @classmethod
    def _get_report_path(cls, case_id: str, report_id: str) -> str:
        return os.path.join(cls._get_case_dir(case_id), f"report_{report_id}.json")

    @classmethod
    def create_case(
        cls,
        title: str,
        investigative_question: str,
        seed_packet: Dict[str, Any],
        case_id: Optional[str] = None,
    ) -> CrimeScopeCase:
        cls._ensure_cases_dir()
        actual_case_id = case_id or f"case_{uuid.uuid4().hex[:12]}"

        case_dir = cls._get_case_dir(actual_case_id)
        os.makedirs(case_dir, exist_ok=True)

        case = CrimeScopeCase(
            case_id=actual_case_id,
            title=title or "Untitled Case",
            investigative_question=investigative_question or "",
            seed_packet=seed_packet or {},
        )
        cls.save_case(case)
        return case

    @classmethod
    def save_case(cls, case: CrimeScopeCase) -> None:
        cls._ensure_cases_dir()
        os.makedirs(cls._get_case_dir(case.case_id), exist_ok=True)
        case.updated_at = datetime.now().isoformat()
        with open(cls._get_case_meta_path(case.case_id), "w", encoding="utf-8") as f:
            json.dump(case.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def get_case(cls, case_id: str) -> Optional[CrimeScopeCase]:
        case_meta = cls._get_case_meta_path(case_id)
        if not os.path.exists(case_meta):
            return None
        with open(case_meta, "r", encoding="utf-8") as f:
            return CrimeScopeCase.from_dict(json.load(f))

    @classmethod
    def list_cases(cls, limit: int = 50) -> list[CrimeScopeCase]:
        cls._ensure_cases_dir()
        cases: list[CrimeScopeCase] = []
        for case_id in os.listdir(cls.CASES_DIR):
            case = cls.get_case(case_id)
            if case:
                cases.append(case)
        cases.sort(key=lambda c: c.created_at, reverse=True)
        return cases[:limit]

    @classmethod
    def save_report(cls, case_id: str, report: Dict[str, Any]) -> str:
        case = cls.get_case(case_id)
        if not case:
            raise ValueError(f"Case does not exist: {case_id}")

        report_id = report.get("report_id") or f"rep_{uuid.uuid4().hex[:12]}"
        report["report_id"] = report_id

        with open(cls._get_report_path(case_id, report_id), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        case.latest_report_id = report_id
        cls.save_case(case)
        return report_id

    @classmethod
    def get_report(cls, case_id: str, report_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        case = cls.get_case(case_id)
        if not case:
            return None

        target_report_id = report_id or case.latest_report_id
        if not target_report_id:
            return None

        report_path = cls._get_report_path(case_id, target_report_id)
        if not os.path.exists(report_path):
            return None

        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)

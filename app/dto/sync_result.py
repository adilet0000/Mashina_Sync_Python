import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


def _json_default(value: Any) -> str:
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


@dataclass
class SyncResult:
    provider: str
    dry_run: bool
    verify: bool = False
    read_count: int = 0
    valid_count: int = 0
    skipped_count: int = 0
    inserted_count: int = 0
    updated_count: int = 0
    unchanged_count: int = 0
    deactivated_count: int = 0
    image_inserted_count: int = 0
    image_deactivated_count: int = 0
    failed_count: int = 0
    verified_count: int = 0
    verification_failed_count: int = 0
    legacy_samples: list[dict[str, Any]] = field(default_factory=list)
    payload_samples: list[dict[str, Any]] = field(default_factory=list)
    diff_samples: list[dict[str, Any]] = field(default_factory=list)
    safety_summary: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors and self.failed_count == 0 and self.verification_failed_count == 0

    def to_lines(self) -> list[str]:
        lines = [
            f"provider={self.provider}",
            f"dry_run={self.dry_run}",
            f"verify={self.verify}",
            f"read_count={self.read_count}",
            f"valid_count={self.valid_count}",
            f"skipped_count={self.skipped_count}",
        ]
        if self.dry_run:
            lines.extend(
                [
                    f"would_insert={self.inserted_count}",
                    f"would_update={self.updated_count}",
                    f"unchanged={self.unchanged_count}",
                    f"would_deactivate={self.deactivated_count}",
                    f"would_insert_images={self.image_inserted_count}",
                    f"would_deactivate_images={self.image_deactivated_count}",
                ]
            )
        else:
            lines.extend(
                [
                    f"inserted_count={self.inserted_count}",
                    f"updated_count={self.updated_count}",
                    f"unchanged_count={self.unchanged_count}",
                    f"deactivated_count={self.deactivated_count}",
                    f"image_inserted_count={self.image_inserted_count}",
                    f"image_deactivated_count={self.image_deactivated_count}",
                ]
            )
        lines.extend(
            [
                f"failed_count={self.failed_count}",
                f"verified_count={self.verified_count}",
                f"verification_failed_count={self.verification_failed_count}",
            ]
        )
        if self.safety_summary:
            lines.append(
                "preflight="
                f"{json.dumps(self.safety_summary, ensure_ascii=False, default=_json_default)}"
            )
        lines.extend(self._sample_lines("legacy_sample", self.legacy_samples))
        lines.extend(self._sample_lines("payload_sample", self.payload_samples))
        lines.extend(self._sample_lines("diff_sample", self.diff_samples))
        lines.extend(f"warning={warning}" for warning in self.warnings)
        lines.extend(f"error={error}" for error in self.errors)
        return lines

    def _sample_lines(self, label: str, samples: list[dict[str, Any]]) -> list[str]:
        return [
            f"{label}_{index}="
            f"{json.dumps(sample, ensure_ascii=False, default=_json_default, sort_keys=True)}"
            for index, sample in enumerate(samples[:3], start=1)
        ]

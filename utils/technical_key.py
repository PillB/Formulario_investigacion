"""Utilidades para construir y expandir la llave técnica."""

from __future__ import annotations

from typing import Callable, Iterable, Iterator

EMPTY_PART = "-"


def _default_normalize(value: str) -> str:
    return (value or "").strip().upper()


def _normalize_collection(
    values: Iterable[str] | None,
    normalize_ids: Callable[[str], str],
    empty: str,
) -> list[str]:
    normalized: list[str] = []
    for value in values or []:
        text = (value or "").strip()
        if not text:
            normalized.append(empty)
            continue
        if text == empty:
            normalized.append(empty)
        else:
            normalized.append(normalize_ids(text))
    return normalized


def build_technical_key(
    case_id: str,
    product_id: str,
    client_id: str,
    team_member_id: str,
    occurrence_date: str,
    claim_id: str,
    *,
    normalize_ids: Callable[[str], str] | None = None,
    empty: str = EMPTY_PART,
) -> tuple[str, str, str, str, str, str]:
    """Construye la llave técnica con placeholders para componentes vacíos."""

    normalizer = normalize_ids or _default_normalize
    occurrence = (occurrence_date or "").strip() or empty
    return (
        normalizer(case_id) or empty,
        normalizer(product_id) or empty,
        normalizer(client_id) or empty,
        normalizer(team_member_id) or empty,
        occurrence,
        normalizer(claim_id) or empty,
    )


def iter_technical_keys(
    case_id: str,
    product_id: str,
    client_ids: Iterable[str] | None,
    team_member_ids: Iterable[str] | None,
    occurrence_date: str,
    claim_ids: Iterable[str] | None,
    *,
    normalize_ids: Callable[[str], str] | None = None,
    empty: str = EMPTY_PART,
) -> Iterator[tuple[str, str, str, str, str, str]]:
    """Genera combinaciones cliente×colaborador×reclamo para la llave técnica."""

    normalizer = normalize_ids or _default_normalize
    normalized_clients = _normalize_collection(client_ids, normalizer, empty) or [empty]
    normalized_team_members = _normalize_collection(team_member_ids, normalizer, empty) or [empty]
    normalized_claims = _normalize_collection(claim_ids, normalizer, empty) or [empty]
    for client_id in normalized_clients:
        for team_member_id in normalized_team_members:
            for claim_id in normalized_claims:
                yield build_technical_key(
                    case_id,
                    product_id,
                    client_id,
                    team_member_id,
                    occurrence_date,
                    claim_id,
                    normalize_ids=normalizer,
                    empty=empty,
                )

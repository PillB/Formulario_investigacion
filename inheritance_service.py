"""Servicios auxiliares para heredar datos del caso hacia un producto."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Set

from settings import TAXONOMIA
from validators import validate_date_text, validate_product_dates


@dataclass(frozen=True)
class InheritanceResult:
    """Resultado de la copia de campos del caso hacia un producto."""

    values: Dict[str, str]
    missing_fields: Set[str]
    invalid_fields: Set[str]

    @property
    def has_missing(self) -> bool:
        return bool(self.missing_fields)

    @property
    def has_invalid(self) -> bool:
        return bool(self.invalid_fields)


class InheritanceService:
    """Contiene la lógica de herencia sin dependencias de Tkinter."""

    _FIELD_ALIASES = {
        "categoria1": ("categoria_1_caso", "categoria1", "categoria_1"),
        "categoria2": ("categoria_2_caso", "categoria2", "categoria_2"),
        "modalidad": ("modalidad_caso", "modalidad"),
        "fecha_ocurrencia": (
            "fecha_de_ocurrencia_caso",
            "fecha_ocurrencia_caso",
            "fecha_ocurrencia",
            "fecha_de_ocurrencia",
        ),
        "fecha_descubrimiento": (
            "fecha_de_descubrimiento_caso",
            "fecha_descubrimiento_caso",
            "fecha_descubrimiento",
            "fecha_de_descubrimiento",
        ),
    }

    @classmethod
    def inherit_product_fields_from_case(cls, case_state: Dict[str, str]) -> InheritanceResult:
        """Devuelve los campos válidos del caso para precargar un producto."""

        missing_fields: Set[str] = set()
        invalid_fields: Set[str] = set()
        values: Dict[str, str] = {}

        cat1 = cls._get_field(case_state, "categoria1")
        cat2 = cls._get_field(case_state, "categoria2")
        modalidad = cls._get_field(case_state, "modalidad")

        cls._copy_taxonomy_fields(cat1, cat2, modalidad, values, missing_fields)

        fecha_oc = cls._get_field(case_state, "fecha_ocurrencia")
        fecha_desc = cls._get_field(case_state, "fecha_descubrimiento")

        cls._copy_dates(fecha_oc, fecha_desc, values, missing_fields, invalid_fields)

        return InheritanceResult(values=values, missing_fields=missing_fields, invalid_fields=invalid_fields)

    @classmethod
    def _get_field(cls, case_state: Dict[str, str], key: str) -> str:
        aliases: Iterable[str] = cls._FIELD_ALIASES.get(key, (key,))
        for alias in aliases:
            if alias in case_state:
                value = case_state.get(alias) or ""
                return value.strip()
        return ""

    @staticmethod
    def _copy_taxonomy_fields(
        cat1: str,
        cat2: str,
        modalidad: str,
        values: Dict[str, str],
        missing_fields: Set[str],
    ) -> None:
        if not cat1:
            missing_fields.add("categoria1")
            return
        if cat1 not in TAXONOMIA:
            missing_fields.add("categoria1")
            return
        values["categoria1"] = cat1

        if not cat2:
            missing_fields.add("categoria2")
            return
        if cat2 not in TAXONOMIA.get(cat1, {}):
            missing_fields.add("categoria2")
            return
        values["categoria2"] = cat2

        if not modalidad:
            missing_fields.add("modalidad")
            return
        if modalidad not in TAXONOMIA.get(cat1, {}).get(cat2, []):
            missing_fields.add("modalidad")
            return
        values["modalidad"] = modalidad

    @staticmethod
    def _copy_dates(
        fecha_oc: str,
        fecha_desc: str,
        values: Dict[str, str],
        missing_fields: Set[str],
        invalid_fields: Set[str],
    ) -> None:
        occ_valid = False
        desc_valid = False
        if fecha_oc:
            occ_error = validate_date_text(fecha_oc, "la fecha de ocurrencia del caso", allow_blank=False)
            if occ_error:
                invalid_fields.add("fecha_ocurrencia")
            else:
                occ_valid = True
                values["fecha_ocurrencia"] = fecha_oc
        else:
            missing_fields.add("fecha_ocurrencia")

        if fecha_desc:
            desc_error = validate_date_text(
                fecha_desc, "la fecha de descubrimiento del caso", allow_blank=False
            )
            if desc_error:
                invalid_fields.add("fecha_descubrimiento")
            else:
                desc_valid = True
                values["fecha_descubrimiento"] = fecha_desc
        else:
            missing_fields.add("fecha_descubrimiento")

        if occ_valid and desc_valid:
            chronology_error = validate_product_dates(
                "producto heredado", fecha_oc, fecha_desc
            )
            if chronology_error:
                invalid_fields.update({"fecha_ocurrencia", "fecha_descubrimiento"})
                values.pop("fecha_ocurrencia", None)
                values.pop("fecha_descubrimiento", None)


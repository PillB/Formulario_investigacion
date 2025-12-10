"""Servicios auxiliares para heredar datos del caso hacia un producto."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Set

from settings import CANAL_LIST, PROCESO_LIST, TAXONOMIA
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
        "canal": ("canal_caso", "canal"),
        "proceso": ("proceso_caso", "proceso"),
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

        cls._copy_taxonomy_fields(cat1, cat2, modalidad, values, missing_fields, invalid_fields)

        fecha_oc = cls._get_field(case_state, "fecha_ocurrencia")
        fecha_desc = cls._get_field(case_state, "fecha_descubrimiento")

        cls._copy_dates(fecha_oc, fecha_desc, values, missing_fields, invalid_fields)

        canal = cls._get_field(case_state, "canal")
        proceso = cls._get_field(case_state, "proceso")

        cls._copy_context_fields(canal, proceso, values, missing_fields, invalid_fields)

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
        invalid_fields: Set[str],
    ) -> None:
        if not cat1:
            missing_fields.add("categoria1")
        elif cat1 not in TAXONOMIA:
            invalid_fields.add("categoria1")
        else:
            values["categoria1"] = cat1

        if not cat2:
            missing_fields.add("categoria2")
        elif cat1 in TAXONOMIA:
            if cat2 in TAXONOMIA.get(cat1, {}):
                values["categoria2"] = cat2
            else:
                invalid_fields.add("categoria2")

        if not modalidad:
            missing_fields.add("modalidad")
        elif cat1 in TAXONOMIA and cat2 in TAXONOMIA.get(cat1, {}):
            if modalidad in TAXONOMIA.get(cat1, {}).get(cat2, []):
                values["modalidad"] = modalidad
            else:
                invalid_fields.add("modalidad")

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

    @staticmethod
    def _copy_context_fields(
        canal: str,
        proceso: str,
        values: Dict[str, str],
        missing_fields: Set[str],
        invalid_fields: Set[str],
    ) -> None:
        if canal:
            if canal in CANAL_LIST:
                values["canal"] = canal
            else:
                invalid_fields.add("canal")
        else:
            missing_fields.add("canal")

        if proceso:
            if proceso in PROCESO_LIST:
                values["proceso"] = proceso
            else:
                invalid_fields.add("proceso")
        else:
            missing_fields.add("proceso")


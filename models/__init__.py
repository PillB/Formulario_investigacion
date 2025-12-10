"""Model helpers for catálogos y cargas masivas."""

from .analitica_catalog import (
    ANALITICA_CATALOG,
    extract_code_from_display,
    find_analitica_by_code,
    find_analitica_by_name,
    format_analitica_option,
    get_analitica_catalog,
    get_analitica_codes,
    get_analitica_display_options,
    get_analitica_names,
)
from .catalog_service import CatalogService, TeamHierarchyCatalog
from .autofill_service import AutofillResult, AutofillService
from .catalogs import (build_detail_catalog_id_index, iter_massive_csv_rows,
                       load_detail_catalogs, normalize_detail_catalog_key,
                       parse_involvement_entries)

__all__ = [
    "ANALITICA_CATALOG",
    "AutofillResult",
    "AutofillService",
    "CatalogService",
    "extract_code_from_display",
    "find_analitica_by_code",
    "find_analitica_by_name",
    "format_analitica_option",
    "get_analitica_catalog",
    "get_analitica_codes",
    "get_analitica_display_options",
    "get_analitica_names",
    "TeamHierarchyCatalog",
    "build_detail_catalog_id_index",
    "iter_massive_csv_rows",
    "load_detail_catalogs",
    "normalize_detail_catalog_key",
    "parse_involvement_entries",
]

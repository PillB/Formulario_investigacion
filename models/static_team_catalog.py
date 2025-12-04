"""Catálogo estático para jerarquía de equipos y agencias.

Provee una jerarquía predeterminada división → área → servicio → puesto y
un catálogo de agencias asociado. Se utiliza como fuente primaria para el
``TeamHierarchyCatalog`` y los valores de ``team_details.csv`` actúan como
complemento opcional.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

TEAM_HIERARCHY_CATALOG: Dict[str, dict] = {
    "2036": {
        "nbr": "GCIA DE DIVISION CANALES DE ATENCION",
        "areas": {
            "2044": {
                "abr": "AREA COMERCIAL LIMA 1",
                "services": {
                    "2862": {
                        "abr": "AREA LIMA 1 - REGION 62",
                        "positions": {
                            "286989": "EJECUTIVO PYME",
                            "263566": "ASESOR DEL CLIENTE LIMA",
                            "183969": "ASISTENTE BEX DIGITAL",
                            "298209": "EJECUTIVO PYME",
                            "45209": "SUPERVISOR DE ASESOR DE CLIENTE",
                            "851": "GERENTE DE AGENCIA",
                        },
                    },
                    "21078": {
                        "nbr": "GERENCIA INBOUND LINEAS SERVICIO Y VENTA",
                        "positions": {
                            "286989": "EJECUTIVO PYME",
                            "263666": "ASESOR DEL CLIENTE LIMA",
                            "851": "GERENTE DE AGENCIA",
                            "290269": "EJECUTIVO PYME",
                        },
                    },
                    "2218": {
                        "nbr": "AREA LIMA 2 - REGION 03",
                        "positions": {
                            "263866": "ASESOR DEL CLIENTE LIMA",
                            "286989": "EJECUTIVO PYME",
                            "266990": "EJECUTIVO PYME SENIOR",
                            "45209": "SUPERVISOR DE ASESOR DE CLIENTE",
                            "263867": "ASESOR DEL CLIENTE PROV",
                            "851": "GERENTE DE AGENCIA",
                        },
                    },
                    "2186": {
                        "positions": {
                            "331164": "ASESOR OUTBOUND PYME",
                        }
                    },
                    "2603": {
                        "abr": "GCIA LINEA SERVICIO DIGITALIDAD Y VENTAS",
                        "positions": {
                            "114179": "SUPERVISOR AUTOR Y BLOQUEOS BXT II -LIMA",
                        },
                    },
                },
            },
            "225": {
                "nbr": "GERENCIA ZONAL DE VENTAS Y TLMK I",
                "positions": {
                    "331104": "ASESOR OUTBOUND PYME",
                },
            },
        },
    },
    "48532": {
        "nbr": "GERENCIA DE NEGOCIOS 528",
        "services": {
            "30981": {
                "nbr": "GERENCIA DE VENTAS TRANSACCIONALES I",
                "positions": {
                    "339572": "EJECUTIVO DE VENTAS PYME",
                    "342941": "SUPERVISOR DE VENTAS PYME",
                },
            },
            "2112": {
                "abr": "REGION 61 - CENTRO",
                "positions": {
                    "263866": "ASESOR DEL CLIENTE LIMA",
                    "296269": "EJECUTIVO PYME",
                    "256959": "EJECUTIVO PYME",
                    "263567": "ASESOR DEL CLIENTE PROV",
                    "263867": "ASESOR DEL CLIENTE PROV",
                },
            },
        },
    },
    "21602": {
        "nbr": "GERENCIA DE BANCA EXCLUSIVA DIGITAL",
        "positions": {
            "297524": "ASISTENTE DE NEGOCIOS BEX DIGITAL",
            "183989": "ASISTENTE BEX DIGITAL",
            "ASISTENTE IZ - OP MAYORISTA POST DESEMB": "ASISTENTE IZ - OP MAYORISTA POST DESEMB",
            "213952": "SUPERVISOR DE OPERACIONES BEX DIGITAL",
            "EJECUTIVO BEX DIGITAL": "EJECUTIVO BEX DIGITAL",
        },
    },
    "26261": {
        "nbr": "TRIBU EXPERIENCIA DEL COLABORADOR",
        "services": {
            "26262": {
                "abr": "OPERATIONAL SUPPORT",
                "positions": {
                    "176962": "SUB GTE ADJ DE PROCESOS",
                },
            },
            "24612": {
                "abr": "REGION 02 - NORTE 1",
                "positions": {
                    "263867": "ASESOR DEL CLIENTE PROV",
                    "286989": "EJECUTIVO PYME",
                    "263866": "ASESOR DEL CLIENTE LIMA",
                },
            },
            "21678": {
                "abr": "REGION 03 - NORTE 2",
                "positions": {
                    "286990": "EJECUTIVO PYME SENIOR",
                    "190734": "PRODUCT OWNER",
                },
            },
        },
    },
    "25801": {
        "nbr": "GERENCIA DE GESTION OPERATIVA",
        "positions": {
            "226007": "GERENTE PYME FACT. NEGOCIABLE",
            "115970": "ASISTENTE DE NEGOCIOS ENALTA",
            "295078": "ASISTENTE DE NEGOCIOS ENALTA",
        },
    },
    "201": {
        "nbr": "TRIBU PYME",
        "services": {
            "26261": {
                "nbr": "GERENCIA DE BANCA ENALTA",
                "positions": {
                    "286990": "EJECUTIVO PYME SENIOR",
                    "183969": "ASISTENTE BEX DIGITAL",
                    "175994": "EJECUTIVO BEX DIGITAL",
                },
            }
        },
    },
    "AAA": {
        "nbr": "GCIA AREA DE SERVICIOS PARA EMPRESAS",
        "services": {
            "120767": {
                "abr": "GERENCIA DE BANCA ENALTA",
                "positions": {
                    "7303624": "QA ENGINEER",
                    "251738": "SCL QUALITY ENGINEER",
                    "257696": "BACKEND JAVA SOFTWARE ENGINEER",
                },
            }
        },
    },
    "175": {
        "nbr": "GCIA AREA INFRAESTRUCTURA Y OPE. DE TI",
        "services": {
            "2200": {
                "abr": "GERENCIA DE OPERACIONES DE TI",
            }
        },
    },
    "174": {
        "nbr": "GCIA DE AREA INGENIERIA Y DESARROLLO TI",
        "services": {
            "23006": {
                "nbr": "GCIA PLANEAMIENTO ESTRATE. TI, DATA Y OP",
                "positions": {
                    "12089": "EMP.PROV. - EMPRESA PROVEEDORA",
                },
            }
        },
    },
    "25237": {
        "nbr": "GCIA AREA ESTRAT. FINANZAS TI, DATA Y OP / TRIBU RIESGOS BDN Y CREDITOS MINORISTAS",
        "services": {
            "23006": {
                "nbr": "GCIA PLANEAMIENTO ESTRATE. TI, DATA Y OP",
                "positions": {
                    "368477": "ANALISTA SR SOPORTE GESTION OPERATIVA",
                },
            },
            "41222": {
                "nbr": "GCIA DE CRED, OPERAC Y PROCES BANCA PERS",
                "positions": {
                    "269077": "ANALISTA DE CAMPO PYME LIMA",
                },
            },
        },
    },
    "26222": {
        "nbr": "GERENCIA CORPORATIVA LEGAL",
        "areas": {
            "ass": {
                "nbr": "GERENCIA DE AREA SOLUCIONES DE NEGOCIOS",
                "services": {
                    "32058": {
                        "abr": "GERENCIA DE GESTION DE EFECTIVO",
                        "positions": {
                            "282352": "ASISTENTE III GESTION OPERATIVA",
                            "317267": "SUB GTE ADJ GESTION OPERATIVA MUNICIPAL",
                        },
                    }
                },
            }
        },
    },
    "GER DIVISION DE RIESGOS NO FINANCIEROS": {
        "nbr": "UO DETECCION DE FRAUDE Y MONITOREO",
    },
    "GCIA DE DIVISION DATA & ANALYTICS": {
        "areas": {
            "GCIA DE AREA DE DATA": {
                "nbr": "GCIA DE DATA & ANALYTICS",
                "positions": {
                    "217777": "DATA ENGINEER ADVANCED",
                },
            }
        },
    },
}

AGENCY_CATALOG: Dict[str, str] = {
    "Agencia Aeropuerto": "192007",
    "Agencia 28 de Julio": "191046",
    "Agencia Asesor del Cliente Lima": "263866",
    "Agencia Cronos": "194057",
    "Agencia Asistente de Negocios en Alta": "711597",
    "Agencia Ejecutivo BEX Digital": "175994",
    "Agencia Supervisor de Operaciones BEX Digital": "215952",
    "Agencia Ejecutivo Pyme": "186989",
    "Agencia Asistente I Soporte Gestión Operativa": "247640",
    "Agencia Analista de Campo Pyme Lima": "226967",
    "Agencia Data Engineer Advanced": "217777",
}


def _label_for(node: dict, default: str) -> str:
    return (node.get("nbr") or node.get("abr") or default).strip()


def _add_row(
    rows: list[dict],
    division_label: str,
    area_label: str,
    service_label: str,
    position_label: str,
    scopes: set[Tuple[str, str]],
    divisions_seen: set[str],
) -> None:
    rows.append(
        {
            "division": division_label,
            "area": area_label,
            "servicio": service_label,
            "puesto": position_label,
            "nombre_agencia": "",
            "codigo_agencia": "",
        }
    )
    if division_label:
        divisions_seen.add(division_label)
    if division_label and area_label:
        scopes.add((division_label, area_label))


def build_team_catalog_rows(
    hierarchy: Dict[str, dict] | None = None, agency_catalog: Dict[str, str] | None = None
) -> List[dict]:
    """Convierte el catálogo estático en filas compatibles con ``TeamHierarchyCatalog``.

    Las filas incluyen una lista de áreas para las que se inyectan agencias por
    defecto, de modo que el UI siempre dispone de valores en cascada incluso
    cuando ``team_details.csv`` está ausente o vacío.
    """

    rows: list[dict] = []
    scopes: set[Tuple[str, str]] = set()
    divisions_seen: set[str] = set()
    hierarchy = hierarchy or TEAM_HIERARCHY_CATALOG
    agency_catalog = agency_catalog or AGENCY_CATALOG

    for division_code, division_data in hierarchy.items():
        division_label = _label_for(division_data, division_code)

        for _, position_label in (division_data.get("positions") or {}).items():
            _add_row(rows, division_label, "", "", position_label, scopes, divisions_seen)

        for _, service_data in (division_data.get("services") or {}).items():
            service_label = _label_for(service_data, "")
            positions = service_data.get("positions") or {}
            if positions:
                for position_label in positions.values():
                    _add_row(rows, division_label, "", service_label, position_label, scopes, divisions_seen)
            elif service_label:
                _add_row(rows, division_label, "", service_label, "", scopes, divisions_seen)

        for _, area_data in (division_data.get("areas") or {}).items():
            area_label = _label_for(area_data, "")
            area_positions = area_data.get("positions") or {}
            for position_label in area_positions.values():
                _add_row(rows, division_label, area_label, "", position_label, scopes, divisions_seen)

            services = area_data.get("services") or {}
            if services:
                for _, service_data in services.items():
                    service_label = _label_for(service_data, "")
                    positions = service_data.get("positions") or {}
                    if positions:
                        for position_label in positions.values():
                            _add_row(
                                rows,
                                division_label,
                                area_label,
                                service_label,
                                position_label,
                                scopes,
                                divisions_seen,
                            )
                    elif service_label:
                        _add_row(
                            rows, division_label, area_label, service_label, "", scopes, divisions_seen
                        )
            elif area_label:
                _add_row(rows, division_label, area_label, "", "", scopes, divisions_seen)

    target_scopes = scopes
    if not target_scopes and divisions_seen:
        target_scopes = {(division_label, "General") for division_label in divisions_seen}

    for division_label, area_label in target_scopes:
        for agency_name, agency_code in agency_catalog.items():
            rows.append(
                {
                    "division": division_label,
                    "area": area_label,
                    "servicio": "",
                    "puesto": "",
                    "nombre_agencia": agency_name,
                    "codigo_agencia": agency_code,
                }
            )

    return rows


__all__ = [
    "AGENCY_CATALOG",
    "TEAM_HIERARCHY_CATALOG",
    "build_team_catalog_rows",
]

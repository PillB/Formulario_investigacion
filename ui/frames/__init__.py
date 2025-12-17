"""Paquete que agrupa los frames dinámicos de la interfaz."""

from .case import CaseFrame
from .clients import ClientFrame
from .norm import NormFrame
from .products import (
    ClaimRow,
    ClientInvolvementRow,
    CollaboratorInvolvementRow,
    InvolvementRow,
    PRODUCT_MONEY_SPECS,
    ProductFrame,
)
from .risk import RiskFrame
from .team import TeamMemberFrame

__all__ = [
    "ClientFrame",
    "CaseFrame",
    "TeamMemberFrame",
    "ProductFrame",
    "RiskFrame",
    "NormFrame",
    "ClaimRow",
    "CollaboratorInvolvementRow",
    "ClientInvolvementRow",
    "InvolvementRow",
    "PRODUCT_MONEY_SPECS",
]

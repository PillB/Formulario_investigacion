"""Paquete que agrupa los frames dinámicos de la interfaz."""

from .clients import ClientFrame
from .norm import NormFrame
from .products import (ClaimRow, InvolvementRow, PRODUCT_MONEY_SPECS,
                       ProductFrame)
from .risk import RiskFrame
from .team import TeamMemberFrame

__all__ = [
    "ClientFrame",
    "TeamMemberFrame",
    "ProductFrame",
    "RiskFrame",
    "NormFrame",
    "ClaimRow",
    "InvolvementRow",
    "PRODUCT_MONEY_SPECS",
]

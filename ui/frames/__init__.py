"""Paquete que agrupa los frames dinámicos de la interfaz."""

from .clients import ClientFrame
from .team import TeamMemberFrame
from .products import ClaimRow, InvolvementRow, PRODUCT_MONEY_SPECS, ProductFrame
from .risk import RiskFrame
from .norm import NormFrame

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

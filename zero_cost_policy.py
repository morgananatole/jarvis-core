"""Política conservadora de custo zero para envio automático via Meta.

Modo padrão: nunca autoriza envio faturável. O uso do app Business
não é uma API gratuita de automação. Este módulo não envia mensagens.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    requires_human: bool = False


def evaluate_outbound(*, transport: str, category: str, verified_free: bool,
                      customer_opt_in: bool, human_approved: bool = False) -> Decision:
    """Gate de autorização, não estimativa de cobrança.

    verified_free deve ser confirmado por mecanismo oficial em tempo de
    execução; nunca inferir apenas de janela de 24 horas, de status HTTP,
    de mensagem iniciada pelo cliente ou de saldo de franquia.
    """
    if not customer_opt_in:
        return Decision(False, "customer_consent_missing")
    if transport != "official_cloud_api":
        return Decision(False, "unsupported_automated_transport")
    if category not in {"service", "utility", "marketing", "authentication"}:
        return Decision(False, "unknown_category")
    if not verified_free:
        return Decision(False, "zero_cost_policy_blocks_potential_charge", True)
    if category == "marketing" and not human_approved:
        return Decision(False, "marketing_requires_explicit_review", True)
    return Decision(True, "official_zero_cost_verified")

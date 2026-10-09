"""Read-only integration diagnostics for the Segundo Eu Capability Forge.

Run: python development_preflight.py --ready-url https://HOST/ready
No credentials, messages, permission grants or code execution are accepted.
"""
import argparse
import json
from dataclasses import asdict, dataclass
from urllib.parse import urlparse
from urllib.request import urlopen


@dataclass(frozen=True)
class IntegrationEvidence:
    app_role_assigned: bool = False
    token_created: bool = False
    official_phone_configured: bool = False
    webhook_subscription_confirmed: bool = False
    configured: bool = False
    storage_available: bool = False
    reply_mode: str = "unknown"
    inbound_confirmed: bool = False
    delivery_confirmed: bool = False
    ai_reply_confirmed: bool = False


def assess(evidence: IntegrationEvidence) -> dict:
    """Build a verification plan; never infer delivery from readiness alone."""
    checks = [
        ("app_role", evidence.app_role_assigned,
         "Conferir função do usuário no app; aplicar somente com autorização específica."),
        ("token", evidence.token_created,
         "Gerar credencial com escopo e duração autorizados; guardar no serviço, nunca no relatório."),
        ("official_phone", evidence.official_phone_configured,
         "Comparar Phone Number ID configurado com o número oficial observado na Meta."),
        ("webhook", evidence.webhook_subscription_confirmed,
         "Conferir callback, campo messages e assinatura do app na WABA oficial."),
        ("configuration", evidence.configured,
         "Corrigir variáveis ausentes indicadas por /ready sem expor seus valores."),
        ("storage", evidence.storage_available,
         "Conferir acesso ao MongoDB antes de processar mensagens."),
        ("inbound", evidence.inbound_confirmed,
         "Enviar mensagem nova de telefone autorizado e verificar processamento no servidor."),
        ("delivery", evidence.delivery_confirmed,
         "Confirmar resposta no telefone ou status delivered; HTTP 200 não comprova entrega."),
    ]
    ready = evidence.configured and evidence.storage_available
    transport = (ready and evidence.official_phone_configured
                 and evidence.webhook_subscription_confirmed
                 and evidence.inbound_confirmed and evidence.delivery_confirmed)
    intelligent = transport and evidence.reply_mode in ("openai", "hybrid") and evidence.ai_reply_confirmed
    return {
        "capability": "integration_preflight", "version": 1,
        "architecture": ["Capability Forge", "Execution Trust Kernel", "Evidence Log"],
        "read_only": True,
        "configuration_ready": ready,
        "official_transport_verified": transport,
        "intelligent_service_verified": intelligent,
        "evidence": asdict(evidence),
        "pending": [{"check": key, "next_action": action}
                    for key, passed, action in checks if not passed],
        "permission_rule": "Uma permissão da plataforma não concede autoridade global ao JARVIS.",
    }


def read_ready(url: str) -> IntegrationEvidence:
    parsed = urlparse(url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment or parsed.path != "/ready"):
        raise ValueError("Use uma URL HTTPS /ready sem credenciais, parâmetros ou fragmentos.")
    # No credential headers; only fields with exact expected types are trusted.
    with urlopen(url, timeout=15) as response:
        raw = response.read(65537)
    if len(raw) > 65536:
        raise ValueError("Resposta maior que o limite de diagnóstico.")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Resposta /ready inválida.")
    mode = payload.get("reply_mode")
    return IntegrationEvidence(
        configured=payload.get("configured") is True,
        storage_available=payload.get("storage_available") is True,
        reply_mode=mode if mode in ("test", "openai", "hybrid") else "unknown",
    )


def main():
    parser = argparse.ArgumentParser(description="Verificar configuração e listar provas que faltam.")
    parser.add_argument("--ready-url", required=True)
    args = parser.parse_args()
    try:
        result = assess(read_ready(args.ready_url))
    except Exception:
        # Do not print exception strings, remote response bodies or URL values.
        result = {"configuration_ready": False, "error": "ready_check_failed",
                  "next_action": "Conferir disponibilidade de /ready e repetir o diagnóstico."}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

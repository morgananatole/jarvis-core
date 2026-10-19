"""Declarative connector inventory. No access requested or connections made."""
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class Capability:
    key: str
    label: str
    permission: str
    purpose: str
    requires_external_authorization: bool = False

CAPABILITIES = (
    Capability("filesystem", "Arquivos locais", "scoped_filesystem", "Ler e gravar pastas escolhidas"),
    Capability("network", "Rede", "network", "Conectar APIs autorizadas"),
    Capability("microphone", "Microfone", "microphone", "Comandos de voz"),
    Capability("notifications", "Notificações", "notifications", "Alertas e andamento"),
    Capability("browser", "Navegador", "browser_control", "Automação de sites permitidos"),
    Capability("drive", "Google Drive", "oauth_drive", "Sincronizar projetos", True),
    Capability("gmail", "Gmail", "oauth_gmail", "Fluxos de mensagens", True),
    Capability("calendar", "Calendário", "oauth_calendar", "Agendamentos", True),
    Capability("models", "Provedores de IA", "api_credentials", "Executar modelos sob orçamento", True),
)

def inventory(granted=()):
    allowed = set(granted)
    return [{"key": c.key, "label": c.label, "purpose": c.purpose,
             "permission": c.permission, "status": "configured" if c.key in allowed else "not_configured",
             "requires_external_authorization": c.requires_external_authorization}
            for c in CAPABILITIES]

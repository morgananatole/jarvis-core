"""Resposta inicial determinística para Nova Vida, sem chamada de IA.

O chamador deve validar consentimento, estado do atendimento e elegibilidade
de envio pela Meta. Este módulo não envia mensagens nem altera contas.
"""
import re
import unicodedata

GREETING = (
    "Olá! Somos a Nova Vida. Eu sou Sobriedade, assistente virtual de IA. "
    "Como podemos ajudar? Para agilizar o atendimento, se desejar, informe: "
    "seu nome, para quem é o tratamento, idade e gênero da pessoa, e qual "
    "substância ela consome. Você pode responder apenas o que se sentir "
    "confortável em compartilhar. Se preferir, posso chamar nossa equipe."
)

def _normalize(value):
    value = unicodedata.normalize("NFKD", value or "")
    return "".join(c for c in value if not unicodedata.combining(c)).strip().lower()

def greeting_for_first_contact(*, business, inbound_text, prior_inbound_count,
                               human_mode=False, do_not_contact=False):
    """Somente primeira mensagem recebida; não interrompe atendimento humano."""
    if business != "nova_vida" or human_mode or do_not_contact:
        return None
    if prior_inbound_count != 0:
        return None
    normalized = _normalize(inbound_text)
    if not normalized or len(normalized) > 80:
        return None
    if re.search(r"\b(humano|atendente|pessoa|urgencia|emergencia|socorro)\b", normalized):
        return None
    return GREETING

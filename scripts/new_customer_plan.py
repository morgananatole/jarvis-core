"""Create a sanitized deployment plan for a new empty PULSE customer.

One customer = one deployment + one MongoDB database. This tool never
creates credentials, starts services, or copies existing CRM records.
"""
import argparse
import json
import re
import secrets


def customer_plan(label, nonce=None):
    if not isinstance(label, str) or not label.strip():
        raise ValueError("customer_name_required")
    slug = re.sub(r"[^a-z0-9]+", "-", label.casefold()).strip("-")[:28]
    if not slug:
        raise ValueError("customer_name_invalid")
    suffix = nonce or secrets.token_hex(5)
    if not re.fullmatch(r"[a-f0-9]{10}", suffix):
        raise ValueError("invalid_identifier")
    identity = slug + "-" + suffix
    return {
        "business_id": identity,
        "mongo_database": "pulse_" + slug.replace("-", "_") + "_" + suffix,
        "environment": {
            "BUSINESS_ID": identity,
            "MONGODB_DATABASE": "pulse_" + slug.replace("-", "_") + "_" + suffix,
        },
        "setup_steps": [
            "Criar um serviço Render separado a partir do mesmo código JARVIS.",
            "Configurar as variáveis BUSINESS_ID e MONGODB_DATABASE neste serviço.",
            "Conectar MongoDB com permissões limitadas ao banco desta empresa.",
            "Configurar credenciais privadas de proprietário, IA e WhatsApp desta empresa.",
            "Confirmar que o banco novo está vazio e que o número da Meta pertence à empresa.",
            "Emitir a licença comercial de 30 dias somente no novo serviço.",
            "Não copiar contatos, históricos, tokens ou arquivos do proprietário para o novo cliente.",
        ],
        "warning": "Plano de provisionamento somente; não cria um serviço nem uma licença.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plano de novo PULSE vazio por empresa")
    parser.add_argument("--empresa", required=True)
    options = parser.parse_args()
    print(json.dumps(customer_plan(options.empresa), ensure_ascii=False, indent=2))

"""Verify paired worker end to end with read-only diagnostic tasks."""
import json
import os
import secrets
import time
from getpass import getpass
from pathlib import Path
from urllib.error import HTTPError, URLError
from connectors.owner_client import OwnerClient


def main():
    config = json.loads((Path.home()/'.jarvis-executor/config.json').read_text())
    os.environ['JARVIS_SERVER'] = config['server']
    os.environ['JARVIS_OWNER_TOKEN'] = getpass('Cole a senha CRM do proprietário e pressione Enter: ')
    try:
        client = OwnerClient()
        device = next((d for d in client.devices() if d['_id'] == config['device_id']), None)
        if not device or not device.get('execution'):
            print('Executor não registrado. Confira se agent run está aberto em outra aba.')
            return
        for capability in ('system.info', 'pulse.doctor', 'pulse.test'):
            task = client.submit(config['device_id'], capability, {}, secrets.token_urlsafe(24))
            print('\nEnviado:', capability, '| tarefa:', task['_id'], flush=True)
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                result = client.status(task['_id'])
                state = result.get('observed_state', result['state'])
                if state in ('succeeded', 'failed', 'uncertain'):
                    print('Resultado:', state, flush=True)
                    output = result.get('output', {})
                    if 'text' in output:
                        print('\n'.join(output['text'].splitlines()[-14:]))
                    else:
                        print(json.dumps(output, ensure_ascii=False, indent=2))
                    if state != 'succeeded':
                        print('Interrompido para conferir a falha. Não repita uma ação incerta.')
                        return
                    break
                time.sleep(3)
            else:
                print('Resultado pendente. Preserve o ID; não repita agora.')
                return
        print('\nVerificação completa: três tarefas concluídas pelo executor.')
    except HTTPError as error:
        print('Falha HTTP:', error.code, '| Confira acesso e conexão. Senha não exibida.')
    except (URLError, TimeoutError, OSError):
        print('Conexão interrompida. Confira o estado da última tarefa antes de repetir.')
    except ValueError:
        print('Configuração, senha ou resposta inválida; valores não exibidos.')
    finally:
        os.environ.pop('JARVIS_OWNER_TOKEN', None)


if __name__ == '__main__':
    main()

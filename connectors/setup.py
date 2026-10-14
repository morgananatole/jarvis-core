"""Interactive setup stores config and keys locally, without changing PULSE."""
import argparse
import json
from pathlib import Path
from connectors.adapters import private_write

def main():
    p=argparse.ArgumentParser();p.add_argument('--server',required=True);p.add_argument('--pulse-dir',default=str(Path.home()/'PULSE_Piloto/PULSE_Conector_Notebook'));p.add_argument('--home',default=str(Path.home()/'.jarvis-executor'));a=p.parse_args()
    from connectors.agent import Client
    root=Path(a.home).expanduser().resolve();path=root/'config.json'
    if path.exists():raise SystemExit('Configuração existente preservada; edite-a para habilitar capacidades.')
    config={'server':a.server,'pulse_dir':a.pulse_dir,'key_file':str(root/'device.pem'),'state_file':str(root/'receipts.sqlite'),
            'enabled':['system.info','pulse.doctor','pulse.test'],'commands':{}}
    Client(config)
    root.mkdir(mode=0o700,parents=True,exist_ok=True)
    private_write(path,json.dumps(config,indent=2));print('Configuração criada. Próximo: python -m connectors.agent pair')
if __name__=='__main__':main()

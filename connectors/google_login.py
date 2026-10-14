"""Explicit local OAuth with read-only scope by default."""
import argparse
from pathlib import Path
from connectors.adapters import private_write

def main():
    p=argparse.ArgumentParser();p.add_argument('--client-file',required=True);p.add_argument('--token-file',default=str(Path.home()/'.jarvis-executor/google-token.json'));p.add_argument('--allow-docs-write',action='store_true');a=p.parse_args()
    from google_auth_oauthlib.flow import InstalledAppFlow
    scopes=['https://www.googleapis.com/auth/drive.metadata.readonly', 'https://www.googleapis.com/auth/documents' if a.allow_docs_write else 'https://www.googleapis.com/auth/documents.readonly']
    creds=InstalledAppFlow.from_client_secrets_file(a.client_file,scopes=scopes).run_local_server(port=0)
    private_write(a.token_file,creds.to_json());print('Google conectado localmente; token não exibido.')
if __name__=='__main__':main()

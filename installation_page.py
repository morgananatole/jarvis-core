"""Public installation entry and downloadable launcher, without embedded credentials."""
from pathlib import Path
from fastapi.responses import HTMLResponse
BASE='https://jarvis-core-ou8d.onrender.com'
def installation():
    return HTMLResponse(Path(__file__).with_name('installation.html').read_text(),headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; script-src 'unsafe-inline' 'self'; style-src 'unsafe-inline'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'"})
def launcher():
    html='<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Abrir JARVIS PULSE</title><h1>JARVIS PULSE</h1><p>Abra a instalação segura. Seu acesso será solicitado no PULSE.</p><a href="'+BASE+'/instalar">Abrir PULSE e instalar</a><p>Precisa de internet. Não contém chave nem instala APK.</p></html>'
    return HTMLResponse(html,headers={'Content-Disposition':'attachment; filename="Abrir_JARVIS_PULSE.html"','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

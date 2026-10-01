"""
Autorização separada (escopo próprio, mais amplo que o de leitura de vídeos) pra
escrever sugestões de classificação de volta na planilha "AUDITORIA - VALIDAÇÃO
MKT INFLU" — que é uma cópia de trabalho da própria Auditoria, não do Marketing.

Fica num token separado do drive_token.json (leitura de vídeos) por princípio de
menor privilégio: cada credencial só tem o escopo que a tarefa dela precisa.

O caminho do client OAuth deixou de ser fixo em 02/09/2026, pelo mesmo motivo
dos outros dois scripts desta pasta. Ver caminho_do_client_oauth.py.

Rode uma vez: py autorizar_sheets_escrita.py
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow

from autorizar_local import autorizar as autorizar_com_servidor_local
from caminho_do_client_oauth import exigir as achar_client_oauth

TOKEN_PATH = os.path.join(os.path.dirname(__file__), "sheets_write_token.json")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def main():
    CLIENT_SECRETS_PATH = achar_client_oauth()
    print(f"Usando o client OAuth de: {CLIENT_SECRETS_PATH}")

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_PATH, SCOPES)
    # NÃO usa mais flow.run_local_server(port=0): ver autorizar_local.py para
    # o motivo (16/09/2026, instalação da Responsável A).
    creds = autorizar_com_servidor_local(flow)

    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    print(f"Token salvo em: {TOKEN_PATH}")
    print("NÃO compartilhe nem suba este arquivo para nenhum lugar.")


if __name__ == "__main__":
    main()

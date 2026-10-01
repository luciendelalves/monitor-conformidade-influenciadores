"""
Autorização separada (escopo drive.file — só dá acesso a arquivos CRIADOS por
esta própria automação, não ao Drive inteiro) para poder subir/criar arquivos
dentro da pasta de trabalho da auditoria no Google Drive.

Fica num token separado do drive_token.json (leitura de vídeos, escopo
drive.readonly) e do sheets_write_token.json (escrita na planilha) por
princípio de menor privilégio: cada credencial só tem o escopo que a tarefa
dela precisa.

O caminho do client OAuth deixou de ser fixo em 02/09/2026, pelo mesmo motivo
dos outros dois scripts desta pasta. Ver caminho_do_client_oauth.py.

Rode uma vez: py autorizar_drive_escrita_arquivo.py
Vai abrir o navegador pedindo para VOCÊ, quem estiver nesta máquina, autorizar.
O token gerado fica com a identidade de quem autorizou.
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow

from autorizar_local import autorizar as autorizar_com_servidor_local
from caminho_do_client_oauth import exigir as achar_client_oauth

TOKEN_PATH = os.path.join(os.path.dirname(__file__), "drive_file_token.json")

# drive.file: só arquivos criados/abertos por esta automação — não dá acesso
# de leitura/escrita ao resto do Drive do usuário.
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


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
    print("NÃO compartilhe nem suba este arquivo para nenhum lugar (Drive, e-mail, zip de backup).")


if __name__ == "__main__":
    main()

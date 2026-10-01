"""
Autorização única para o script de validação de avisos regulatórios ter acesso
de LEITURA à árvore inteira de pastas do Google Drive (sem depender de a pasta
já ter sido aberta manualmente, ao contrário do conector MCP do Claude Code).

Reaproveita o mesmo client OAuth já registrado no projeto COAF, só pedindo um
escopo novo (Drive, somente leitura). Gera um token separado do usado pelo COAF,
para não misturar escopos entre os dois projetos.

O CAMINHO DO CLIENT DEIXOU DE SER FIXO EM 02/09/2026. Ele estava escrito como
C:\\Users\\auditor\\Documents\\COAF\\oauth_client.json, ou seja, o caminho
da máquina de uma pessoa. Em qualquer outra máquina este script falhava com uma
mensagem que apontava para o arquivo faltar, quando o problema era o caminho não
ser dela. Descoberto ao escrever o guia de instalação da primeira colaboradora.
Ver caminho_do_client_oauth.py.

Rode uma vez: py autorizar_drive.py
Vai abrir o navegador pedindo para VOCÊ, quem estiver nesta máquina, autorizar.
O token gerado fica com a identidade de quem autorizou.
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow

from autorizar_local import autorizar as autorizar_com_servidor_local
from caminho_do_client_oauth import exigir as achar_client_oauth

TOKEN_PATH = os.path.join(os.path.dirname(__file__), "drive_token.json")

# Somente leitura — nunca escrita, não precisamos alterar nada no Drive.
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


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

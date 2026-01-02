from __future__ import annotations

import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

from backend.app.config import settings

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def main() -> None:
    client_path = Path(settings.google_oauth_client_file)
    token_path = Path(settings.google_oauth_token_file)

    if not client_path.exists():
        raise SystemExit(
            f"Arquivo OAuth client não encontrado em {client_path}. "
            "Baixe o credentials.json do Google Cloud e coloque nesse caminho."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(client_path), SCOPES)
    creds = flow.run_local_server(port=0)

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")

    # sanity check
    json.loads(token_path.read_text(encoding="utf-8"))
    print(f"Token salvo em: {token_path}")


if __name__ == "__main__":
    main()


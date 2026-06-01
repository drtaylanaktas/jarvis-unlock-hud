"""One-time Google OAuth flow → token.json (read-only Gmail/Calendar/Tasks).

Setup:
  1. Google Cloud Console → create OAuth client (Desktop app) → download as
     core/credentials.json
  2. Add yourself as a test user on the OAuth consent screen.
  3. Run:  python core/google_auth.py
Both credentials.json and token.json are gitignored.
"""
from __future__ import annotations
import os

from google_client import load_config, CRED_PATH, TOKEN_PATH
from google_auth_oauthlib.flow import InstalledAppFlow


def main() -> None:
    cfg = load_config()
    scopes = cfg["google"]["scopes"]
    if not os.path.exists(CRED_PATH):
        raise SystemExit(f"Missing {CRED_PATH}. Download an OAuth Desktop client from "
                         "Google Cloud Console and save it there.")
    flow = InstalledAppFlow.from_client_secrets_file(CRED_PATH, scopes)
    creds = flow.run_local_server(port=0)
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())
    print(f"✅ Authorized. Token saved to {TOKEN_PATH}")


if __name__ == "__main__":
    main()

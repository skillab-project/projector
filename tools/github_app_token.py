#!/usr/bin/env python3
import argparse
import os
import time
import urllib.request

import jwt


def read_private_key(args):
    if args.private_key:
        return args.private_key
    if args.private_key_file:
        with open(args.private_key_file, encoding="utf-8") as key_file:
            return key_file.read()
    if os.environ.get("GITHUB_APP_PRIVATE_KEY"):
        return os.environ["GITHUB_APP_PRIVATE_KEY"]
    if os.environ.get("GITHUB_APP_PRIVATE_KEY_FILE"):
        with open(os.environ["GITHUB_APP_PRIVATE_KEY_FILE"], encoding="utf-8") as key_file:
            return key_file.read()
    raise SystemExit("GitHub App private key missing")


def create_jwt(app_id, private_key):
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 540,
        "iss": app_id,
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def create_installation_token(app_id, installation_id, private_key):
    app_jwt = create_jwt(app_id, private_key)
    request = urllib.request.Request(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        headers={
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "projector-jenkins-github-app-token",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        data = response.read().decode("utf-8")

    import json

    return json.loads(data)["token"]


def main():
    parser = argparse.ArgumentParser(description="Create a GitHub App installation token for Jenkins.")
    parser.add_argument("--app-id", default=os.environ.get("GITHUB_APP_ID"), required=not os.environ.get("GITHUB_APP_ID"))
    parser.add_argument(
        "--installation-id",
        default=os.environ.get("GITHUB_APP_INSTALLATION_ID"),
        required=not os.environ.get("GITHUB_APP_INSTALLATION_ID"),
    )
    parser.add_argument("--private-key")
    parser.add_argument("--private-key-file")
    args = parser.parse_args()

    print(create_installation_token(args.app_id, args.installation_id, read_private_key(args)))


if __name__ == "__main__":
    main()

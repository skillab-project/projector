# GitHub App for Jenkins

Use a GitHub App when Jenkins should publish PR comments, commit comments, and commit statuses as a bot instead of a personal user.

## App Settings

Create the app under the GitHub organization:

- Name: `projector-jenkins`
- Homepage URL: Jenkins base URL
- Webhook: disabled
- Repository access: only `skillab-project/projector`

Permissions:

- Commit statuses: read/write
- Contents: read/write
- Issues: read/write
- Pull requests: read
- Metadata: read

After creation:

- install the app on the repository
- copy the App ID
- copy the Installation ID from the installation URL
- generate and download a private key

## Jenkins Credentials

Store these Jenkins credentials:

- `github-app-id`: secret text with the App ID
- `github-app-installation-id`: secret text with the Installation ID
- `github-app-private-key`: secret file with the downloaded private key

Generate an installation token inside the CI image:

```sh
GITHUB_TOKEN=$(python tools/github_app_token.py \
  --app-id "$GITHUB_APP_ID" \
  --installation-id "$GITHUB_APP_INSTALLATION_ID" \
  --private-key-file "$GITHUB_APP_PRIVATE_KEY_FILE")
```

Then pass `GITHUB_TOKEN` to `tools/github_statuses.py`.

The resulting PR comments, commit comments, and commit status will be authored by the GitHub App bot.

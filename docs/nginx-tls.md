# Nginx / TLS Setup

Nginx terminates TLS and reverse-proxies to the Vault container. Vault
itself never sees plaintext HTTP from the internet, and its `8200` port is
never published to the host directly.

## 1. DNS

Point your domain (e.g. `vault.example.com`) at the public IP of the Docker
Swarm node(s) running the `nginx` service (it's deployed with `mode:
global`, so it runs on every node in the swarm and binds host ports 80/443
via `mode: host`).

## 2. Set your real domain

Replace every occurrence of `vault.example.com` with your actual domain in:

- `nginx/config/nginx.conf` (two `server_name` lines)
- `vault/config/config.hcl` (`api_addr`)

## 3. TLS certificate

Place your certificate and private key at:

```
nginx/certs/certs.pem
nginx/certs/private.key
```

These paths are **gitignored** — never commit real certs/keys. Options for
obtaining them:

- **Let's Encrypt** (recommended for anything internet-facing): use
  `certbot` on the host, or an ACME sidecar container, then copy/symlink
  the issued `fullchain.pem`/`privkey.pem` into `nginx/certs/` as
  `certs.pem`/`private.key`. Set up renewal (cron or systemd timer) since
  Let's Encrypt certs expire every 90 days — this repo does not automate
  renewal for you.
- **Internal/private CA**: fine for internal-only tools like this one — just
  make sure any clients (browsers, the sync script's host) trust your CA,
  or you'll hit `SSLError: CERTIFICATE_VERIFY_FAILED` when running
  `sync_ip_inventory.py` from a host that doesn't have your CA in its trust
  store.
- **Self-signed**: works for quick testing, but browsers and the Python
  `requests` library will both complain — only use for local experiments.

## 4. Basic auth (optional, `.htpasswd`)

The compose file mounts `../nginx/.htpasswd` into the container. This repo
does **not** include one — Vault has its own auth (tokens, userpass,
LDAP, OIDC, etc.), so a second layer of basic auth in front of it is
optional defense-in-depth, not a requirement.

If you want it, generate one with:

```bash
htpasswd -c nginx/.htpasswd yourusername
```

...and add the corresponding `auth_basic` / `auth_basic_user_file`
directives to the `location /` block in `nginx.conf` (not included by
default, since Vault's UI login flow and basic auth can interact awkwardly
— test carefully if you add this).

**Do not commit `.htpasswd`** — it's gitignored.

## 5. Logs

Nginx logs to `../nginx/logs/` on the host (mounted volume) — also
gitignored, since access logs can contain sensitive info like source IPs
and request patterns.

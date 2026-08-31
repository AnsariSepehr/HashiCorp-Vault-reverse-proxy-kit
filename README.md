# Vault + Nginx Reverse Proxy Deployment

A self-hosted [HashiCorp Vault](https://www.vaultproject.io/) instance, deployed
as a single-node Docker Swarm stack, sitting behind an **Nginx** reverse proxy
that terminates TLS. Includes a small Python utility to keep a KV v2
"IP → hostname" inventory in Vault in sync with a spreadsheet.

> **⚠️ This repo is a sanitized template.** Domains, certificates, tokens, and
> real inventory data have all been replaced with placeholders / sample data.
> Do not commit your real `.htpasswd`, TLS private key, Vault unseal keys, or
> root token to this (or any public) repository. See
> [Security notes](#security-notes) below.

## Repo layout

```
.
├── docker-compose.vault.yml      # Docker Swarm stack: Vault + Nginx
├── vault/
│   └── config/
│       └── config.hcl            # Vault server config (Raft storage, plain-TCP listener)
├── nginx/
│   └── config/
│       └── nginx.conf            # Reverse proxy + TLS termination for Vault UI/API
├── scripts/
│   ├── sync_ip_inventory.py      # Spreadsheet -> Vault KV v2 sync script
│   └── sample-data/
│       └── ip-inventory-sample.xlsx
└── docs/
    ├── vault-setup.md            # Initializing/unsealing Vault, policies, tokens
    ├── nginx-tls.md              # Certs, .htpasswd, DNS
    └── ip-inventory-sync.md      # How the sync script works, usage, examples
```

## What this deploys

- **Vault** (`hashicorp/vault:1.14.0`), single node, [Integrated Storage
  (Raft)](https://developer.hashicorp.com/vault/docs/concepts/integrated-storage)
  backend, UI enabled, listening on plain HTTP internally (`8200`) since TLS
  is handled by Nginx in front of it.
- **Nginx**, terminating TLS on 443, redirecting 80 → 443, reverse-proxying
  to the Vault container over the internal `vault-net` overlay network. Vault
  itself is **not** published to the host — only Nginx is (ports 80/443).
- A **KV v2 secrets engine** in Vault used as a lightweight IP-address
  inventory / mini CMDB (IP → hostname, OS, and any other fields you want),
  and a script to keep it in sync with a spreadsheet.

## Quick start

1. Read [`docs/vault-setup.md`](docs/vault-setup.md) and
   [`docs/nginx-tls.md`](docs/nginx-tls.md) first — you need to supply your
   own domain, certificate, and `.htpasswd` before this stack is usable.
2. Copy this repo to your Docker Swarm manager node.
3. Fill in the placeholders (see below).
4. Deploy:
   ```bash
   docker stack deploy -c docker-compose.vault.yml vault
   ```
5. Initialize and unseal Vault — see
   [`docs/vault-setup.md`](docs/vault-setup.md).
6. (Optional) Set up the IP inventory KV engine and run the sync script —
   see [`docs/ip-inventory-sync.md`](docs/ip-inventory-sync.md).

## Placeholders you must replace

| File | Placeholder | Replace with |
|---|---|---|
| `vault/config/config.hcl` | `vault.example.com` | your real domain |
| `nginx/config/nginx.conf` | `vault.example.com` (x2) | your real domain |
| `nginx/certs/` | *(empty, gitignored)* | your `certs.pem` + `private.key` |
| `nginx/.htpasswd` | *(not included, gitignored)* | your own basic-auth file, if used |

## Security notes

- **Never commit**: TLS private keys, `.htpasswd`, Vault unseal keys, Vault
  root/service tokens, or your real inventory spreadsheet if it contains
  real credentials. All of these are covered by `.gitignore` in this repo —
  double check before pushing if you add new sensitive files.
- The included `docker-compose.vault.yml` disables `mlock` and runs with
  `IPC_LOCK` — standard for containerized Vault, but review Vault's
  [production hardening
  guide](https://developer.hashicorp.com/vault/tutorials/day-one-raft/production-hardening)
  before using this for anything beyond a lab/small internal deployment.
- This stack has **one Vault node** (no HA). Fine for small teams/labs;
  for production, look at a multi-node Raft cluster.
- Vault's KV UI sorts secret keys as plain strings, so IPs won't list in
  numeric order (`10.10.10.10` sorts before `10.10.10.2`). This is a
  cosmetic Vault UI limitation, not a bug in this repo — see
  [`docs/ip-inventory-sync.md`](docs/ip-inventory-sync.md) for details.

## License

MIT — see [`LICENSE`](LICENSE). Use at your own risk; review everything
before deploying to any environment that matters.

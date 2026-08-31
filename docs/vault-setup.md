# Vault Setup

This covers deploying the stack, initializing Vault, unsealing it, and
setting up the KV v2 engine used by the inventory sync script.

## 1. Deploy the stack

On your Docker Swarm manager node:

```bash
docker stack deploy -c docker-compose.vault.yml vault
docker service ls
```

You should see `vault_vault` (1/1) and `vault_nginx` (global, 1/1 per node).

Vault's port `8200` is **only** reachable inside the `vault-net` overlay
network — it is intentionally not published to the host. All access goes
through Nginx on 80/443. Keep it this way unless you have a specific reason
to expose it directly (e.g. local CLI access on the host — if you want that,
add a published port for 8200 in the compose file, understanding this
bypasses Nginx's TLS termination and any auth you put in front of it).

## 2. Find the Vault container

```bash
docker ps
# vault_vault.1.<task-id>
```

All `vault` CLI commands below are run either:
- inside that container (`docker exec -it <container> sh`, then set
  `VAULT_ADDR=http://127.0.0.1:8200` inside the shell), or
- from any machine that can reach `https://vault.example.com` (your real
  domain), using the `vault` CLI or plain `curl`/the API.

> Env vars set with `docker exec -e VAR=value ...` only apply to that one
> exec session — they are not inherited from your host shell and do not
> persist across separate `docker exec` invocations. Either export them
> fresh each time, or better, run administrative scripts from the host
> against `https://vault.example.com` instead of execing into the
> container repeatedly.

## 3. Initialize Vault (first time only)

```bash
vault operator init
```

This outputs **5 unseal key shares** and **1 initial root token** by
default. Threshold is 3 of 5 shares to unseal, unless you configure
otherwise.

**Store these somewhere safe and offline** (password manager, sealed
document, etc.) — anyone with enough key shares can unseal Vault, and the
root token has full access. Never commit these to git, ever.

## 4. Unseal Vault

Each Vault server process starts **sealed** and needs `threshold` number of
unseal keys supplied before it will serve requests:

```bash
vault operator unseal   # repeat with a different key each time, x3 by default
```

Check status any time with:

```bash
vault status
```

## 5. Log in

```bash
export VAULT_ADDR="https://vault.example.com"
vault login   # paste your root token, or a scoped token (see below)
```

## 6. Create a KV v2 engine for the IP inventory

```bash
vault secrets enable -path=IPTable -version=2 kv
```

You can also do this from the Vault UI: **Secrets engines → Enable new
engine → KV → set path to `IPTable` → Version 2**.

To wipe it and start clean (e.g. before a fresh bulk import):

```bash
vault secrets disable IPTable
vault secrets enable -path=IPTable -version=2 kv
```

This removes all data **and** version history under that mount — there's no
undo, so be sure before running it.

## 7. (Recommended) Create a scoped token for the sync script

Avoid using the root token for routine imports. Create a policy that can
only read/write this one KV mount:

```hcl
# policies/ip-inventory-write.hcl
path "IPTable/data/*" {
  capabilities = ["create", "update", "read"]
}
path "IPTable/metadata/*" {
  capabilities = ["read", "list"]
}
```

```bash
vault policy write ip-inventory-write policies/ip-inventory-write.hcl
vault token create -policy=ip-inventory-write -ttl=24h
```

Use the resulting token (not root) as `VAULT_TOKEN` when running
`sync_ip_inventory.py`. A short TTL means a leaked token stops being useful
quickly.

## Read-only access (for people who just need to look up hostnames)

```hcl
# policies/ip-inventory-read.hcl
path "IPTable/data/*" {
  capabilities = ["read", "list"]
}
path "IPTable/metadata/*" {
  capabilities = ["list"]
}
```

```bash
vault policy write ip-inventory-read policies/ip-inventory-read.hcl
vault token create -policy=ip-inventory-read
```

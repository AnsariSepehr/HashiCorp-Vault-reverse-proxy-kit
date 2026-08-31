# IP Inventory Sync (Spreadsheet → Vault KV v2)

`scripts/sync_ip_inventory.py` keeps a Vault KV v2 mount in sync with an
Excel spreadsheet, so you can look up "what is this IP / what's it running /
who owns it" from Vault's UI or API instead of hunting through a
spreadsheet.

## Why Vault for this?

It's a bit unconventional (Vault is normally for secrets), but it works
well as a lightweight, access-controlled, versioned mini-CMDB:

- KV v2 keeps version history, so you can see when a hostname/owner changed.
- You can scope read-only tokens/policies to just this mount (see
  [`vault-setup.md`](vault-setup.md)) for people who just need lookups.
- One less system to stand up if you already run Vault.

If your inventory grows large or needs richer querying, a real CMDB or
database is a better fit long-term — this is meant for small/medium
internal lists (tens to low hundreds of hosts).

## Spreadsheet format

First column must be the IP address. Every other column becomes a field on
that IP's Vault secret automatically — **no code changes needed** to add a
new column later (e.g. `Username`, `Owner`, `Location`, whatever you want).

See [`scripts/sample-data/ip-inventory-sample.xlsx`](../scripts/sample-data/ip-inventory-sample.xlsx)
for the expected shape:

| IP | SeverName | OS | Username |
|---|---|---|---|
| 10.10.10.1 | core-switch-01 | IOS | |
| 10.10.10.2 | vcenter-lab | Photon | administrator |
| 10.10.10.3 | gitlab-lab | CentOS-7 | root |
| 10.10.10.4 | | | |
| ... | | | |

- Rows with an IP but every other column blank are skipped entirely (not
  written to Vault) — useful for unused IPs you're tracking as "reserved but
  empty" in the spreadsheet without cluttering Vault.
- **Blank cells are not written as empty fields.** If `Username` is blank
  for a row, no `username` key is created for that secret at all — you
  won't end up with fields like `"username": ""` sitting in Vault.
- If a cell that previously had a value is cleared in the spreadsheet, the
  script currently does **not** delete that field from Vault on the next
  sync (it only adds/updates, never removes). If you need clearing a cell
  to also delete the corresponding Vault field, that's a small addition —
  open an issue / adjust the script's merge logic in `main()`.

## What "diff-based" means

On each run, for every IP row in the spreadsheet, the script:

1. Fetches the existing secret at `IPTable/data/<ip>` from Vault, if any.
2. Compares each spreadsheet column's value against what's already stored.
3. Only issues a write if something actually changed (new field, changed
   value, etc.) — unchanged IPs are left alone entirely, so you don't create
   pointless new KV versions or trigger unnecessary audit log entries.
4. Fields already in Vault that aren't columns in your spreadsheet are
   preserved (merge, not overwrite) — e.g. if someone manually added a
   `Notes` field via the UI, re-running the script won't wipe it.

## Usage

```bash
pip3 install openpyxl requests --break-system-packages

export VAULT_ADDR="https://vault.example.com"
export VAULT_TOKEN="hvs.xxxxxxxxxxxxxxxxxxxxxxxx"   # ideally a scoped token, see vault-setup.md
export VAULT_KV_MOUNT="IPTable"                      # optional, defaults to IPTable

python3 scripts/sync_ip_inventory.py scripts/sample-data/ip-inventory-sample.xlsx
```

Sample output:

```
CREATED 10.10.10.2 -> {'SeverName': 'vcenter-lab', 'OS': 'Photon', 'Username': 'administrator'}
CREATED 10.10.10.3 -> {'SeverName': 'gitlab-lab', 'OS': 'CentOS-7', 'Username': 'root'}
...
Done. Created: 8, Updated: 0, Unchanged (skipped write): 0, Blank rows skipped: 2, Failed: 0
```

Run it again immediately with no changes to the spreadsheet, and everything
reports as `Unchanged` — a good sanity check that diffing is working.

## Where to run it from

Run this **on the host**, not inside the Vault container — the official
Vault Docker image is minimal Alpine with no package manager access for
Python packages. The script only needs HTTP(S) access to
`$VAULT_ADDR`, so any machine that can reach your Vault URL works (it
doesn't need to be the Vault server itself).

## A note on Vault UI sort order

Vault's KV browser sorts keys **as strings**, not numerically, so IPs will
list like `10.10.10.1`, `10.10.10.10`, `10.10.10.2`, ... rather than
numeric order. This is a Vault UI limitation, not something this script
controls. In practice, use the **Filter secrets** search box in the UI to
jump straight to an IP rather than scrolling — that's the realistic
day-to-day usage pattern for a lookup table like this anyway.

## Automating this (optional)

To keep Vault continuously in sync, run this on a schedule (cron/systemd
timer) pointed at wherever your canonical spreadsheet lives, or trigger it
from CI when the spreadsheet changes in its own repo. Not included here
since it depends heavily on where you keep the source spreadsheet.

#!/usr/bin/env python3
"""
Sync an IP inventory spreadsheet into HashiCorp Vault KV v2 — diff-based.

- Reads column headers dynamically from row 1 (first column must be the IP).
  Any other column (ServerName/hostname, OS, Username, whatever you add later)
  becomes a field on the secret automatically.
- For each IP, fetches the existing secret from Vault (if any), compares it
  field-by-field against the spreadsheet row, and only writes back if
  something actually changed (new field, changed value, etc).
- Existing fields not present as columns in the spreadsheet are left alone
  (merge, not overwrite) — e.g. if you manually added a "Notes" field in
  Vault's UI, it won't be wiped out by re-running this script.
- Skips rows where all non-IP columns are blank.

Usage:
    export VAULT_ADDR="https://vault.example.com"
    export VAULT_TOKEN="hvs.xxxxxxxxxxxxxxxxxxxxxxxx"
    python3 sync_ip_inventory.py sample-data/ip-inventory-sample.xlsx

Requires: pip3 install openpyxl requests --break-system-packages

Security note:
    VAULT_TOKEN is a credential. Never commit it, hardcode it, or pass it
    on the command line where it could end up in shell history. Always
    supply it via environment variable, ideally from a secrets manager or
    a short-lived token, and prefer a token whose policy is scoped to
    write access on this KV mount only (see docs/vault-setup.md for an
    example policy).
"""

import sys
import os
import openpyxl
import requests


def normalize(value):
    """Treat None and '' as equivalent, and stringify everything else,
    so comparisons between Vault (always strings) and Excel (mixed types)
    are apples-to-apples."""
    if value is None:
        return ""
    return str(value).strip()


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 import_ip_list.py <path-to-xlsx>")
        sys.exit(1)

    xlsx_path = sys.argv[1]
    vault_addr = os.environ.get("VAULT_ADDR")
    vault_token = os.environ.get("VAULT_TOKEN")

    if not vault_addr or not vault_token:
        print("ERROR: set VAULT_ADDR and VAULT_TOKEN environment variables first.")
        sys.exit(1)

    mount = os.environ.get("VAULT_KV_MOUNT", "IPTable")  # the KV v2 mount path

    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb.active

    rows_iter = ws.iter_rows(values_only=True)
    headers = list(next(rows_iter))
    field_cols = headers[1:]  # everything after IP is a dynamic field

    session = requests.Session()
    session.headers.update({"X-Vault-Token": vault_token})

    created, updated, unchanged, skipped, failed = 0, 0, 0, 0, 0

    for row in rows_iter:
        ip = row[0]
        if not ip:
            continue

        new_fields = {}
        for col_name, val in zip(field_cols, row[1:]):
            v = normalize(val)
            if v:  # only keep non-empty fields; blanks are simply not written
                new_fields[col_name] = v

        # skip rows that are entirely blank besides the IP
        if not new_fields:
            skipped += 1
            continue

        url = f"{vault_addr}/v1/{mount}/data/{ip}"

        # 1. fetch existing secret, if any
        existing_fields = {}
        get_resp = session.get(url)
        if get_resp.status_code == 200:
            existing_fields = get_resp.json().get("data", {}).get("data", {}) or {}
        elif get_resp.status_code not in (404,):
            print(f"WARN    {ip}: unexpected GET status {get_resp.status_code}: {get_resp.text}")

        # 2. merge: start from existing fields, overlay with spreadsheet values
        merged_fields = dict(existing_fields)
        changed = False
        for col_name, new_val in new_fields.items():
            old_val = normalize(existing_fields.get(col_name))
            if old_val != new_val:
                changed = True
            merged_fields[col_name] = new_val

        if not changed:
            unchanged += 1
            continue

        # 3. write back only if something changed
        payload = {"data": merged_fields}
        resp = session.post(url, json=payload)
        if resp.status_code not in (200, 204):
            print(f"FAILED  {ip}: {resp.status_code} {resp.text}")
            failed += 1
        else:
            if existing_fields:
                print(f"UPDATED {ip} -> {merged_fields}")
                updated += 1
            else:
                print(f"CREATED {ip} -> {merged_fields}")
                created += 1

    print(
        f"\nDone. Created: {created}, Updated: {updated}, "
        f"Unchanged (skipped write): {unchanged}, Blank rows skipped: {skipped}, "
        f"Failed: {failed}"
    )


if __name__ == "__main__":
    main()

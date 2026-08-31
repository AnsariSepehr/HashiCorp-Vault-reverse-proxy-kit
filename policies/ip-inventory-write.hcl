# Scoped policy for the sync script - write access to the IP inventory
# KV mount only, nothing else in Vault.
#
# Apply with:
#   vault policy write ip-inventory-write policies/ip-inventory-write.hcl
#   vault token create -policy=ip-inventory-write -ttl=24h

path "IPTable/data/*" {
  capabilities = ["create", "update", "read"]
}

path "IPTable/metadata/*" {
  capabilities = ["read", "list"]
}

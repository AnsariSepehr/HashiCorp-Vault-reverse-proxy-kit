# Scoped policy for people who just need to look up hostnames by IP -
# read-only access to the IP inventory KV mount, nothing else in Vault.
#
# Apply with:
#   vault policy write ip-inventory-read policies/ip-inventory-read.hcl
#   vault token create -policy=ip-inventory-read

path "IPTable/data/*" {
  capabilities = ["read", "list"]
}

path "IPTable/metadata/*" {
  capabilities = ["list"]
}

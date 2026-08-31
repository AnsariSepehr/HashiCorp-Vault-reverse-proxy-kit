# Vault server config
ui = true

# Integrated storage using Raft
storage "raft" {
  path    = "/vault/data"
  node_id = "node1"
}

# Listener - plain TCP inside the container only.
# TLS is terminated at Nginx, not here (see nginx/config/nginx.conf).
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = true
}

# External address Vault should advertise to clients.
# Replace with your own domain.
api_addr     = "https://vault.example.com"
cluster_addr = "http://127.0.0.1:8201"

# Allow Vault to start without mlock (containers can't use it by default
# unless granted IPC_LOCK, which this stack does — you can remove this line
# if you'd rather rely on cap_add: IPC_LOCK only).
disable_mlock = true

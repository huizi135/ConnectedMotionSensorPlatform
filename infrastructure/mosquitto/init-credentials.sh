#!/bin/sh
set -eu
umask 077

mode="${1:-reuse}"
case "$mode" in new|reuse|check-new) ;; *) echo "Invalid initialization mode" >&2; exit 2 ;; esac
if { [ "$mode" = new ] || [ "$mode" = check-new ]; } && [ -f /auth/.initialized ]; then
    echo "Existing broker credentials found but local client credentials are missing. Stop and recover the local file; no credentials overwritten." >&2
    exit 2
fi

if [ "$mode" = check-new ]; then
    echo "No existing initialized auth volume found."
    exit 0
fi

IFS= read -r simulator_password
IFS= read -r backend_password
# Accept stdin delivered with either LF or Windows CRLF.
simulator_password=$(printf '%s' "$simulator_password" | tr -d '\r')
backend_password=$(printf '%s' "$backend_password" | tr -d '\r')
[ -n "$simulator_password" ] && [ -n "$backend_password" ]
case "$simulator_password$backend_password" in
    *[!A-Za-z0-9_-]*) echo "Unexpected credential characters" >&2; exit 2 ;;
esac

# Always create fresh plaintext input; never re-hash an already hashed file.
# -U converts the temporary file in place without passwords in command arguments.
trap 'rm -f /auth/password_file.pending' EXIT
printf 'simulator:%s\nbackend:%s\n' "$simulator_password" "$backend_password" > /auth/password_file.pending
mosquitto_passwd -U /auth/password_file.pending
cp /input/acl /auth/acl.pending
chown 1883:1883 /auth /auth/password_file.pending /auth/acl.pending
chmod 0750 /auth
chmod 0600 /auth/password_file.pending /auth/acl.pending
mv /auth/password_file.pending /auth/password_file
mv /auth/acl.pending /auth/acl
: > /auth/.initialized
chown 1883:1883 /auth/.initialized
chmod 0600 /auth/.initialized
unset simulator_password backend_password
echo "MQTT credentials and ACL initialized. No passwords printed."

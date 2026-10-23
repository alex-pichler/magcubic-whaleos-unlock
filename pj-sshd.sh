#!/usr/bin/env bash
# Root SSH server on the projector (no adb root needed).
#
# dropbear is cross-built static for arm-linux-musleabihf with zig and started
# through ISystemControl.systemCmd (uid 0, system_control domain). Android has
# no /etc/passwd and no /etc/shells, so:
#   * /system/etc/passwd is bind-mounted from a one-line synthetic file
#   * dropbear is patched to skip the /etc/shells whitelist
#   * DEFAULT_ROOT_PATH is patched to include /data/local/ssh/bin, where the
#     server-side `scp` lives
# The bind mount and the listener are runtime-only; rerun after a reboot.
#
# usage: ./pj-sshd.sh
#        PJ_SSH_PORT=22 PJ_SSH_PUBKEY=~/.ssh/id_alex_pc.pub ./pj-sshd.sh
set -u
cd "$(dirname "$0")"
PORT="${PJ_SSH_PORT:-22}"
PJ_HOST="${PJ_HOST:-<PROJECTOR_IP>}"
PUBKEY_FILE="${PJ_SSH_PUBKEY:-$HOME/.ssh/id_alex_pc.pub}"
BIN_DIR="$(dirname "$0")/ssh"
export PJ_HOST

for f in dropbear dropbearkey scp; do
  [ -x "$BIN_DIR/$f" ] || { echo "missing $BIN_DIR/$f — see ssh/README.md" >&2; exit 1; }
done
[ -f "$PUBKEY_FILE" ] || { echo "no public key at $PUBKEY_FILE" >&2; exit 1; }

adb connect "$PJ_HOST:5555" >/dev/null 2>&1
adb devices | grep -q "$PJ_HOST:5555[[:space:]]*device" || {
  echo "no adb device at $PJ_HOST:5555" >&2; exit 1; }

for f in dropbear dropbearkey scp; do
  adb push "$BIN_DIR/$f" "/data/local/tmp/$f" >/dev/null || exit 1
done

PUB="$(cat "$PUBKEY_FILE")"

./pjroot.sh "mkdir -p /data/local/ssh/bin /dev/ssh; chmod 700 /dev/ssh; \
  mv -f /data/local/tmp/dropbear /data/local/tmp/dropbearkey /data/local/ssh/; \
  mv -f /data/local/tmp/scp /data/local/ssh/bin/scp; \
  chmod 755 /data/local/ssh/dropbear /data/local/ssh/dropbearkey /data/local/ssh/bin/scp; \
  printf 'root:x:0:0:root:/data:/system/bin/sh\n' > /data/local/ssh/passwd; \
  grep -q ' /system/etc/passwd ' /proc/mounts || mount --bind /data/local/ssh/passwd /system/etc/passwd; \
  [ -f /data/local/ssh/host_key ] || /data/local/ssh/dropbearkey -t ed25519 -f /data/local/ssh/host_key >/dev/null 2>&1; \
  echo '$PUB' > /dev/ssh/authorized_keys; chown root:root /dev/ssh/authorized_keys; chmod 600 /dev/ssh/authorized_keys; \
  kill \$(cat /data/local/ssh/dropbear.pid 2>/dev/null) 2>/dev/null; sleep 1; \
  setsid /data/local/ssh/dropbear -F -p $PORT -r /data/local/ssh/host_key -s -D /dev/ssh \
      -P /data/local/ssh/dropbear.pid >/data/local/ssh/dropbear.log 2>&1 & sleep 1.5; \
  chmod 644 /data/local/ssh/dropbear.log; tail -2 /data/local/ssh/dropbear.log; \
  ps -A -o PID,USER,NAME | grep -w dropbear"

echo
echo "ssh -p $PORT -i ${PUBKEY_FILE%.pub} -o IdentitiesOnly=yes root@$PJ_HOST"
echo "scp -O -P $PORT -i ${PUBKEY_FILE%.pub} -o IdentitiesOnly=yes file root@$PJ_HOST:/data/local/tmp/"

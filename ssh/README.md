# Root sshd on the projector

dropbear 2026.94, statically linked, built for `arm-linux-musleabihf` with zig
0.16. It is started as uid 0 through `ISystemControl.systemCmd` (transact 386 on
the `@1.1` interface) and ends up in the `system_control` SELinux domain, which
on this permissive build means full root capabilities.

`adb root` is not available (`ro.debuggable=0`, adbd is built for production),
so this replaces it for interactive use.

## Use

```sh
./pj-sshd.sh                       # (re)install + start, port 22
ssh -i ~/.ssh/id_alex_pc -o IdentitiesOnly=yes root@<device>
scp -O -i ~/.ssh/id_alex_pc -o IdentitiesOnly=yes file root@<device>:/data/local/tmp/
```

A `~/.ssh/config` entry makes it painless:

```
Host pj
    HostName <PROJECTOR_IP>
    User root
    Port 22
    IdentityFile ~/.ssh/id_alex_pc
    IdentitiesOnly yes
```

`scp` needs `-O` (legacy protocol): modern OpenSSH uses SFTP by default and this
device has no `sftp-server` binary. The server-side `scp` is dropbear's, installed
in `/data/local/ssh/bin`, which required patching `DEFAULT_ROOT_PATH` at build
time because dropbear overwrites `PATH` for root sessions.

`IdentitiesOnly=yes` matters: when the agent offers several keys dropbear
sometimes stalls after accepting the first one. A single explicit key is
reliable (tested 5/5).

The session looks like:

```
uid=0(root) gid=0(root) groups=0(root) context=u:r:system_control:s0
```

Key-only auth (`-s`), port 22, no password logins. Everything is runtime-only:
after a reboot rerun `./pj-sshd.sh` (see Persistence below).

## What Android forces us to shim

1. **No `/etc/passwd`** — `/system/etc/passwd` is 0 bytes, and bionic resolves
   `root` from its built-in `android_ids` table, which a musl binary does not
   have. `pj-sshd.sh` bind-mounts a one-line file over it:

   ```
   root:x:0:0:root:/data:/system/bin/sh
   ```

2. **No `/etc/shells`** — dropbear validates the login shell against
   `getusershell()`; musl returns nothing when the file is missing, so every
   login was rejected with "has invalid shell". The source is patched to accept
   any non-empty shell path (see below).

3. **`PATH` is forced** — dropbear sets `DEFAULT_ROOT_PATH`
   (`/usr/sbin:/usr/bin:/sbin:/bin`) for root logins, and those paths don't exist
   on Android. Patched to `/data/local/ssh/bin:/system/bin:/system/xbin` so the
   server-side `scp` is reachable.

4. **`authorized_keys` path checks** — dropbear refuses a key file whose parent
   directories are group-writable, and `/data` is `0771 system:system`. The key
   therefore lives in `/dev/ssh/authorized_keys` (tmpfs, root-owned, 0600) and
   is passed with `-D /dev/ssh`.

## Rebuild

```sh
curl -LO https://matt.ucc.asn.au/dropbear/releases/dropbear-2026.94.tar.bz2
tar xjf dropbear-2026.94.tar.bz2 && cd dropbear-2026.94
ZIG=~/.local/share/mise/installs/zig/0.16.0/zig
./configure --host=arm-linux-musleabihf CC="$ZIG cc -target arm-linux-musleabihf" \
  --disable-zlib --disable-syslog --disable-lastlog --disable-utmp --disable-utmpx \
  --disable-wtmp --disable-wtmpx --disable-pututline --disable-pututxline \
  --disable-loginfunc --disable-pam --disable-shadow --enable-static
# patch: accept any shell (src/svr-auth.c, before setusershell())
#   goto goodshell;
make -j8 PROGRAMS="dropbear dropbearkey"
```

Copy `dropbear` and `dropbearkey` here. Static musl binaries run unmodified on
the device (verified with a hello-world first).

## Notes / limits

- No `sftp`: only `scp` (legacy) is provided. `sftp` needs an `sftp-server`
  binary, which isn't built here.
- The bind mount survives until reboot or `umount /system/etc/passwd`; the
  listener until killed. Nothing is written to `/system`.
- Root login over the network: on the lab AP this is isolated, on the home LAN
  it is reachable from any host on the subnet. Key-only, but consider binding
  with `-p <wifi-ip>:2222` or dropping `-s` + adding a password if that matters.

## Persistence — why there is no init service yet

Android's `init` only reads `.rc` files from read-only partitions. On this
device that is a hard wall:

- `/` is the system image, `ro.boot.veritymode=enforcing`, bootloader `locked`
  → `/system` cannot be remounted rw, so no `.rc` and no binary can be added.
- No `exec` of anything under `/data` in any `.rc`; no `install-recovery.sh`;
  `/data/adb` exists but is empty (no Magisk, no `su`).

So a real `service sshd ...` at boot needs a **patched boot image** (Magisk or a
custom ramdisk): `boot_b` is a standard `ANDROID!` image, and we have root to
`dd` it back. That is the only path to `init` auto-start, and it needs a reboot
plus a rollback plan (A/B does not switch slots on a failed boot by itself).

The zero-risk alternative is a host-side watchdog: a systemd unit on alex-pc
that, whenever the projector answers on 5555, ensures sshd is running. It needs
a root path that exists at boot — currently that means launching Kodi (the
`systemCmd` gadget lives in its process), which is ugly.

Everything else (keys, host key, binaries) already lives on `/data` and survives
reboots; only the bind mount and the listener have to be recreated.

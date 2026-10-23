# MagCubic / WhaleOS projector: minimal root path

This repo holds only the scripts for the one chain that gave a working root
command path and persistence on a MagCubic projector (Zeasn WhaleOS, Android 13,
Amlogic, `user` build, locked AVB). It starts from a Kodi addon, gets root without
adb or a signing key, installs a small boot app, and brings up a root SSH server
that survives reboots. Other recon, dead ends and store work are left out on purpose.

Legal: own-device use only (a device you own). No manufacturer code or binaries
are redistributed here. Store-channel details are withheld pending vendor disclosure.

## The chain

```
PC --TCP:9998--> Kodi process (uid 10039, addon script.pjshell)
                   |  exec() of the sent Python (pyeval)
                   |  ctypes -> libnativehelper -> JNI
                   v
                 android.os.HwBinder.getService(
                   "vendor.amlogic.hardware.systemcontrol@1.1::ISystemControl", "default")
                   |  raw transact(386, ...)   systemCmd(string)
                   v
                 vendor system_control daemon (uid 0, u:r:system_control:s0)
                   |  system(cmd)
                   v
                 root shell
                   |  setprop persist.sys.concert.tinsel 1   (opens the install gate)
                   |  pm install pjctl.apk                    (boot app)
                   |  stm_at env edit                          (SELinux permissive on cold boot)
                   v
                 BOOT_COMPLETED -> pjctl -> systemCmd(386) -> restart.sh -> dropbear root sshd :22
```

Only step 1 needs Kodi. After the boot app is installed, a cold boot brings root SSH
back on its own. Kodi is not involved.

## Order of dependencies

Root comes first and needs no adb. The Kodi addon -> pyeval -> JNI -> `HwBinder.transact(386)`
-> `systemCmd` chain is the whole root primitive. It is the only thing that gives uid 0 on
this box, and nothing in it depends on adb.

adb on `<PROJECTOR_IP>:5555` is enabled afterward, using that root: root repairs the adb key
file (`/data/misc/adb/adb_keys`) and restarts adbd. No script in this repo performs
that key fix. Once adb is up, `pj-sshd.sh` and `pjroot.sh` use it only as a convenience
transport (`adb push`, `adb forward`).

A reader who prefers not to use adb can run the same commands through `sc_cmd.py`
(`systemCmd`) or the Kodi channel (`pjsh2.py`) instead. `pjroot.sh` starts its listener
through `pjeval.py` and does not need adb for that part; only the forward to the PC does.

## Files

| Path | Role |
|---|---|
| `addon-src/addon.xml`, `addon-src/default.py` | Kodi service addon. Opens pyeval on `:9998` and a bind shell on `:9999`. |
| `addon-src/script.pjshell-1.0.1.zip` | The same addon packed for Kodi "Install from zip". Rebuilt from `addon-src/`. |
| `pjeval.py` | PC side of pyeval: sends a Python file, prints what it printed. |
| `pjsh2.py` | PC side of the `:9999` shell: runs commands, returns their output. |
| `sc_cmd.py` | The root gadget. Runs inside Kodi: JNI, `HwBinder.transact(386)`, `systemCmd`. Edit `ARGS` for the command to run as root. |
| `sc_call.py` | Same plumbing for other ISystemControl calls. Used for the `stm_at` env write (code 59). |
| `pjroot.sh` | Root shell helper: starts a loopback root listener through `sc_cmd.py`, reached from the PC via `adb forward` (optional transport). Used by `pj-sshd.sh`. |
| `pj-sshd.sh` | Installs dropbear and its key/passwd files under `/data/local/ssh`, starts the root sshd. Bootstrap only. |
| `restart.sh` | Runs on each boot as root (from the boot app). Recreates `/dev/ssh`, the passwd bind mount, and starts dropbear. |
| `pjctl/` | The boot app (`BootReceiver`, `MainActivity`, `Pjctl`), its manifest and `build.sh`. |
| `env-edits/README.md` | The `stm_at` bootloader env edit: keeps SELinux permissive on cold boot. Values not included. |
| `ssh/README.md` | How to build the static dropbear binaries that `pj-sshd.sh` expects in `ssh/`. Binaries not included. |

## Prerequisites

- The projector on your LAN. Set `PJ_HOST=<PROJECTOR_IP>` for every script below.
- Kodi running on the box (only for step 1).
- PC: `python3`. For `pjctl/build.sh`: Android SDK (build-tools 34.0.0, platform android-33) and a JDK.
- adb is optional. `pj-sshd.sh` and `pjroot.sh` use `adb` to `<PROJECTOR_IP>:5555` as a transport,
  once adbd is up from root (see Order of dependencies). Without it, run the same commands through
  `sc_cmd.py` or `pjsh2.py`.
- The dropbear binaries (`dropbear`, `dropbearkey`, `scp`) in `ssh/`. Build them as described in `ssh/README.md`.

## Step 0: install the addon

Kodi, Settings, System, Add-ons: allow unknown sources. Then Add-ons, Install from zip,
pick `script.pjshell-1.0.1.zip`. The addon re-binds `:9998` and `:9999` at every Kodi start.

Check the channel:

```sh
PJ_HOST=<PROJECTOR_IP> python3 -I pjeval.py 'print(1+1)'
# 2
```

If this hangs, the addon is not running and nothing else will work.

## Step 1: root command execution

Edit `ARGS` in `sc_cmd.py`, then run it inside Kodi:

```sh
# the target file must exist and be owned by the app before root writes to it
PJ_HOST=<PROJECTOR_IP> python3 -I pjsh2.py \
  ': > /data/data/org.xbmc.kodi/cache/syscmd_id.txt'
PJ_HOST=<PROJECTOR_IP> python3 -I pjeval.py < sc_cmd.py
# transact 386 ok, verifySuccess=True
PJ_HOST=<PROJECTOR_IP> python3 -I pjsh2.py \
  'cat /data/data/org.xbmc.kodi/cache/syscmd_id.txt'
# uid=0(root) ... context=u:r:system_control:s0
```

`systemCmd` returns nothing, so output has to go to a file the app can read.
Root-created files are `0600 root`, which is why the file is pre-created.

For an interactive root shell over `adb forward`, use `./pjroot.sh` (no arguments)
or `./pjroot.sh 'id; getprop'` for one command. The listener itself is started through
`pjeval.py` without adb; the adb forward is only how the PC reaches it.

## Step 2: root sshd (bootstrap)

`pj-sshd.sh` pushes dropbear, dropbearkey and scp to `/data/local/ssh`, creates a
synthetic `/etc/passwd`, generates a host key, and starts `dropbear -s` on port 22.
It runs its root commands through `pjroot.sh` and pushes the binaries with `adb push`.

Before the first run, also copy your public key to `/data/local/ssh/authorized_keys`.
`restart.sh` copies from that path on every boot; `pj-sshd.sh` only writes the
tmpfs copy in `/dev/ssh`.

```sh
PJ_HOST=<PROJECTOR_IP> PJ_SSH_PUBKEY=~/.ssh/<your_key>.pub ./pj-sshd.sh
ssh -i ~/.ssh/<your_key> -o IdentitiesOnly=yes root@<PROJECTOR_IP>
# uid=0(root) ... context=u:r:system_control:s0
```

Key-only login. `scp` needs `-O` (legacy protocol), since the box has no `sftp-server`.

## Step 3: persistence (boot app)

1. Open the install gate (root, persists across reboot):

   ```sh
   /system/bin/setprop persist.sys.concert.tinsel 1
   ```

   Run it from the root SSH shell, or put it in `ARGS` of `sc_cmd.py`. Use absolute paths; the daemon's `PATH` is not a shell's.

2. Build the boot app on the PC:

   ```sh
   cd pjctl && ./build.sh        # produces pjctl.apk (not shipped)
   ```

3. Put `pjctl.apk` on the device at `/data/local/tmp/pjctl.apk`. This repo does not
   script the transfer. The original work used `cat ... | ssh` once root SSH was up.

4. Install and launch once. The launch clears the stopped state, so Android delivers
   `BOOT_COMPLETED` to the app:

   ```sh
   /system/bin/pm install -r /data/local/tmp/pjctl.apk     # prints Success
   /system/bin/am start -n com.pj.ctl/.MainActivity
   ```

`BootReceiver` runs `Pjctl.run()` on boot. It calls `systemCmd(386)` with
`sh /data/local/ssh/restart.sh`, which brings dropbear back up.

## Step 4: bootloader env, SELinux permissive on cold boot

`pjctl` depends on SELinux being permissive. A cold boot otherwise comes up
enforcing and the `HwBinder` call fails. The fix is one token in the vendor `stm_at`
env variable (`factorymode 0` to `factorymode 1` in its final cold-boot branch).
Full procedure, the revert snippet and the CRC check are in `env-edits/README.md`.
Dump your own copy of the env partition before you change it.

## Verify

Cold power-cycle the projector, wait for boot, then:

```sh
ssh -i ~/.ssh/<your_key> -o IdentitiesOnly=yes root@<PROJECTOR_IP> 'id; getenforce; cat /data/local/tmp/pjctl.status'
# uid=0(root) ... Permissive, ok
```

Kodi does not need to be running for this. The original run recorded this as passing on 2026-10-23.

## Gotchas

- Token and code must match. `systemCmd` is code 386 on the `@1.1` token. `sc_call.py`
  as shipped uses the `@1.0` token.
- Absolute paths only. `/system/bin/logcat` works, `logcat` does not.
- `systemCmd` returns void. Redirect output to a file the app can read, or to `/sdcard`.
- Root-created files are `0600 root`. Pre-create the target as the app, or `chmod` it in the same root command.
- Background processes need `setsid` and a redirect, otherwise `system()` kills them:
  `setsid cmd </dev/null >/data/local/x.log 2>&1 &`
- Kodi must stay up for step 1. The VM and the `:9998` server die with it.
- Nothing here writes boot images, efuses or the factory trigger files. The only
  bootloader write is the `stm_at` edit in step 4.

## Not included

- Vendor binaries, jars, `.so`/`.dex` files, decompiled framework or vendor code.
  This includes the vendor bootloader script text.
- Prebuilt `pjctl.apk` (build it with `pjctl/build.sh`) and the dropbear binaries (see `ssh/README.md`).
- Recon captures, notes, decompiled store code, test tooling, and factory trigger files.
- Store-channel details, withheld pending vendor disclosure.

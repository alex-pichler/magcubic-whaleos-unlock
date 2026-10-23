# pjctl — Kodi-free root entry point

Replaces the Kodi addon as the thing that re-establishes root SSH after a reboot. A ~4 KB app:

- `BootReceiver` (BOOT_COMPLETED / QUICKBOOT_POWERON / `com.pj.ctl.RUN`) → `Pjctl.run()`.
- `Pjctl.run()` lifts the hidden-API blacklist (meta-reflection; SELinux is permissive), then calls
  `android.os.HwBinder.getService("vendor.amlogic.hardware.systemcontrol@1.1::ISystemControl")` and
  `transact(386, …)` = `systemCmd("sh /data/local/ssh/restart.sh …")` → root dropbear comes back.
- `MainActivity` runs the same thing on launch, so it can be triggered without a reboot.

Same root primitive as the Kodi path (`WORKING-PATH.md`), just in our own app, so Kodi + `script.pjshell`
can be retired. Depends on SELinux permissive (factorymode=1) exactly as the Kodi path did.

## Build & install
    ./build.sh
    cat pjctl.apk | ssh projector 'cat > /data/local/tmp/pjctl.apk; pm install -r /data/local/tmp/pjctl.apk'
    ssh projector 'am start -n com.pj.ctl/.MainActivity'   # launch once: tests it AND clears stopped-state

Install needs the Zeasn gate open (`setprop persist.sys.concert.tinsel 1`, root). The one-time launch is
required so Android delivers BOOT_COMPLETED to it (stopped-state apps don't receive it).

## Verified 2026-10-23
Real cold power-cycle: box came up `getenforce=Permissive factorymode=1` (via the `stm_at` env edit,
`../env-edits/`), `BootReceiver` fired on `BOOT_COMPLETED` → `systemCmd(386)` → `restart.sh` recreated
`/dev/ssh` + the `/etc/passwd` bind-mount + started root dropbear; `ssh projector` connected as `uid=0`
hands-free. No Kodi, no pyeval, no adb.

Depends on SELinux permissive, which now persists across cold boots thanks to the `stm_at` edit
(see `../env-edits/README.md`). Without that edit, a cold boot comes up enforcing and the
`HwBinder` call fails — re-enable factory mode first.

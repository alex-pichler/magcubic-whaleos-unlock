# u-boot env edit: stm_at (permissive-on-cold-boot)

The vendor `stm_at` env variable runs from `preboot` on every boot. On a cold boot
with no factory USB trigger, its final `else` branch does `setenv factorymode 0`
(SELinux enforcing). The edit changes that one token to `setenv factorymode 1`, so
SELinux stays permissive across cold power cycles. Nothing else in the variable is
changed.

The original and patched values are NOT included in this repo (vendor bootloader
script). Dump your own before editing:

    cat /dev/block/by-name/env > /data/local/tmp/env.before   # whole partition; keep as your revert source

Apply (as root, via the Kodi pyeval or pjctl channel) with `sc_call.py`, code 59:

    call(59, [("s","ubootenv.var.stm_at"), ("s", <patched value>)], "", "setBootEnv")

Then re-dump `/dev/block/by-name/env` and check both 64 KB copies' CRC32 (offset 0,
over data[4:0x10000]) and that no other variable changed.

Note: `sc_call.py` as shipped uses the ISystemControl @1.0 token. Code 59 was taken
from the recon code map, which is not included here; verify the token and code pair
before applying.

#!/system/bin/sh
# Re-establish root SSH after a reboot (run as root via pjctl/systemCmd on BOOT_COMPLETED).
mkdir -p /dev/ssh; chmod 700 /dev/ssh
cp -f /data/local/ssh/authorized_keys /dev/ssh/authorized_keys
chown root:root /dev/ssh/authorized_keys; chmod 600 /dev/ssh/authorized_keys
# synthetic passwd so dropbear knows 'root' (runtime bind-mount, gone on reboot)
printf 'root:x:0:0:root:/data:/system/bin/sh\n' > /data/local/ssh/passwd
grep -q ' /system/etc/passwd ' /proc/mounts || mount --bind /data/local/ssh/passwd /system/etc/passwd
kill $(cat /data/local/ssh/dropbear.pid 2>/dev/null) 2>/dev/null; sleep 1
setsid /data/local/ssh/dropbear -F -p 22 -r /data/local/ssh/host_key -s -D /dev/ssh -P /data/local/ssh/dropbear.pid >/data/local/ssh/dropbear.log 2>&1 &
sleep 1.5; tail -2 /data/local/ssh/dropbear.log
# keep network adb (tcp:5555) off each boot; factory mode re-enables it. USB adb unaffected.
setprop service.adb.tcp.port -1
setprop ctl.restart adbd

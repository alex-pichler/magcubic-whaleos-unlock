#!/usr/bin/env bash
# Build pjctl.apk — the Kodi-free root entry point.
# BootReceiver -> HwBinder.transact(386, systemCmd) -> sh /data/local/ssh/restart.sh -> root sshd.
# Needs: Android SDK (build-tools 34, platform android-33), a JDK. Install gate must be open on
# the device (persist.sys.concert.tinsel=1) to `pm install` the result.
set -e
cd "$(dirname "$0")"
SDK="${ANDROID_HOME:-$HOME/Android}"; BT="$SDK/build-tools/34.0.0"; AJ="$SDK/platforms/android-33/android.jar"
rm -rf out; mkdir -p out
javac --release 11 -classpath "$AJ" -d out $(find src -name '*.java')   # avoid anon classes: R8+JDK26 NPEs on them
"$BT/d8" --min-api 21 --lib "$AJ" --output out $(find out -name '*.class')
test -f out/classes.dex
"$BT/aapt2" link -I "$AJ" --manifest AndroidManifest.xml --min-sdk-version 21 --target-sdk-version 31 -o out/base.apk
( cd out && python3 -c "import zipfile;z=zipfile.ZipFile('base.apk','a',zipfile.ZIP_STORED);z.write('classes.dex','classes.dex');z.close()" )
[ -f key.jks ] || keytool -genkeypair -keystore key.jks -storepass android -keypass android -alias pj -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=pjctl" >/dev/null 2>&1
"$BT/zipalign" -f 4 out/base.apk out/pjctl-aligned.apk
rm -f pjctl.apk
"$BT/apksigner" sign --ks key.jks --ks-pass pass:android --key-pass pass:android --out pjctl.apk out/pjctl-aligned.apk
echo "built: pjctl.apk"

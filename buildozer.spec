[app]

title = IDEA2APK
package.name = idea2apk
package.domain = com.nexgen

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,txt

version = 0.1

requirements = python3==3.11.5,hostpython3==3.11.5,kivy==2.3.0

orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 21
android.ndk = 25b
p4a.branch = v2024.01.21
android.build_tools_version = 34.0.0
android.accept_sdk_license = True

android.archs = arm64-v8a, armeabi-v7a

# ZIP export uses Android's system file picker (Storage Access Framework).
# No broad storage permission is required.
android.permissions = INTERNET

[buildozer]

log_level = 2
warn_on_root = 1



[app]

title = IDEA2APK
package.name = idea2apk
package.domain = com.nexgen

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas

version = 0.1

requirements = python3==3.12.10,hostpython3==3.12.10,kivy==2.3.0

orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 26
android.ndk = 25b
android.build_tools_version = 34.0.0
android.accept_sdk_license = True

android.archs = arm64-v8a, armeabi-v7a

android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

[buildozer]

log_level = 2
warn_on_root = 1

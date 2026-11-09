

[app]

title = IDEA2APK
package.name = idea2apk
package.domain = com.nexgen

source.dir = .
source.include_exts = py,kv,png,jpg,atlas

version = 0.1

requirements = python3,kivy==2.3.2

p4a.branch = develop

orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 21
android.ndk = 28c
android.accept_sdk_license = True
android.permissions = INTERNET
android.archs = arm64-v8a

[buildozer]

log_level = 2
warn_on_root = 1

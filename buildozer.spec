[app]
title = MEXC Mobile Scanner
package.name = mexcmobilescanner
package.domain = org.nowafapps
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,md,ttf,db
version = 1.0.0
requirements = python3,kivy==2.3.1,requests,urllib3,charset-normalizer,idna,certifi,arabic-reshaper,python-bidi,openssl,sqlite3
orientation = portrait,landscape
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK
android.api = 35
android.minapi = 23
android.ndk = 27c
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.enable_androidx = True

[buildozer]
log_level = 2
warn_on_root = 1

[app]
title = SAR VOC
package.name = sarvoc
package.domain = org.sarvoc
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,html,css,txt
source.exclude_dirs = .buildozer,bin,__pycache__,backend,Profile,Games,VoiceRooms
source.exclude_patterns = *.pyc,*.md,*.sql
version = 1.0
requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.1,supabase==2.27.0,pyjnius==1.6.1
presplash.filename = %(source.dir)s/presplash.png
icon.filename = %(source.dir)s/icon.png
orientation = portrait
fullscreen = 0
android.accept_sdk_license = True
android.permissions = android.permission.INTERNET,android.permission.RECORD_AUDIO
android.minapi = 24
android.api = 33
android.archs = arm64-v8a,armeabi-v7a
android.allow_backup = True
android.debug_artifact = apk
android.release_artifact = aab
[buildozer]
log_level = 2
warn_on_root = 0

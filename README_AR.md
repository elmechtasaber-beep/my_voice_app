# SAR VOC — merged Android project

هذا المشروع يجمع نسخة Voice Rooms + Supabase + USDT/BEP20 + لعبة الفواكه، مع إعداد Buildozer مأخوذ من المشروع القديم الذي كان يبني APK بنجاح.

## الملفات الأساسية
- `main.py`: نقطة تشغيل التطبيق.
- `login_screen.*`: تسجيل الدخول وخلفية الدخول.
- `rooms_screen.*`: الغرف الصوتية.
- `voice_room_screen.*`: الغرفة + لعبة الفواكه.
- `wallet_screen.*`: المحفظة وشحن USDT/BEP20.
- `icon.png`: أيقونة التطبيق.
- `presplash.png`: شاشة البداية.
- `buildozer.spec`: إعداد البناء.

## ملاحظة مهمة
ملفات `backend/` و `Games/` و `Profile/` موجودة للمشروع/الخادم لكنها مستثناة من APK بواسطة `buildozer.spec`. يجب تنفيذ SQL/Edge Functions في Supabase بشكل منفصل حتى تعمل وظائف اللعبة والشحن.

## Termux
بعد وضع المشروع في `~/my_voice_app`:
```bash
cd ~/my_voice_app
buildozer android debug
```

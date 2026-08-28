# SAR VOC — My Voice merged / FINAL

هذه النسخة هي نقطة البناء النهائية الموحدة:

- اسم التطبيق: **SAR VOC**
- package: **org.sarvoc.sarvoc**
- اسم الملف الناتج يعتمد على Buildozer، والـAPK يرفع تلقائياً كـArtifact باسم `sar-voc-apk`.
- تم الإبقاء على واجهات My Voice المدمجة: تسجيل الدخول، الغرف الصوتية، الغرفة، المحفظة، الألعاب/اللوحات الموجودة، Supabase وRealtime.
- تم اعتماد `icon.png` و`presplash.png` الموجودين في المشروع.
- تم حذف كاش `.buildozer` و`__pycache__` من الحزمة.
- تم تنظيف Workflow ليبدأ بناء Android من بيئة نظيفة ويتأكد أن APK موجود قبل رفعه.

## GitHub

ارفع محتويات هذا المجلد إلى المستودع ثم نفّذ Push إلى `main`، أو شغّل Workflow يدوياً من Actions.

## Termux

```bash
cd ~/SAR_VOC_MYVOICE_FINAL
buildozer android clean
buildozer android debug
```

بعد نجاح البناء ستجد APK داخل `bin/`.

> ملاحظة: لا تضع GitHub Token أو مفاتيح سرية أو Supabase `service_role` داخل المشروع أو الـAPK.

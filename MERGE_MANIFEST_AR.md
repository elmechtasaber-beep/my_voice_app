# سجل الدمج

المصدر: SAR_VOC_READY_BUILD + مكونات My Voice الموجودة في SAR_VOC_FINAL_MERGED.

القاعدة المعتمدة للبناء هي التطبيق المعياري الحالي في الجذر، وليس الـmain.py القديم أحادي الملف من النسخة الاحتياطية؛ لأن النسخة المعيارية تحتوي على ملفات الشاشات وSupabase وRealtime وWallet وVoice Room بشكل منفصل وقابل للبناء.

تم تغيير namespace الخاص بوحدة Profile المصدرية إلى `org.sarvoc.profile` لتفادي بقاء اسم الحزمة القديم. وحدة Profile نفسها تبقى خارج حزمة Buildozer الحالية كما كان محدداً في `buildozer.spec`.

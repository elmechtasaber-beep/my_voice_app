# Profile — Supabase Direct Connected

تم ربط شاشة Profile مباشرة بـ Supabase REST.

- Project URL: `https://kwlovnyznahfkyhvmyzv.supabase.co`
- Publishable key: موجود داخل التطبيق كـ publishable/anon key فقط.
- لا يوجد `service_role` داخل APK.
- يجب أن تكون جلسة Supabase محفوظة في `supabase_session/access_token` أو تمرير `access_token` في Intent.
- الرصيد يُقرأ من `wallets.balance`.
- بيانات الملف تُقرأ من `profiles`.

> ملاحظة: هذه الشاشة لا تنشئ جلسة دخول من نفسها؛ تسجيل الدخول في التطبيق الرئيسي هو الذي يوفر access token.

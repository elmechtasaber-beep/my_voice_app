# APP_SUPABASE_CONNECTED_V2

تمت مراجعة النسخة السابقة وإصلاح نقاط الربط التي كانت غير متطابقة مع قاعدة البيانات:

- recharge request أصبح RPC بدلاً من INSERT مباشر.
- `send_gift` يستعمل `p_coin_cost` الصحيح.
- سجل transactions لا يطلب `balance_after` لأنه غير موجود في schema.
- approve_recharge محمي ضد استدعاء المستخدم العادي.
- Agora App ID محدث.

هذه ليست بعد نسخة APK إنتاجية كاملة: دفع حقيقي يحتاج مزود دفع/Backend، وAgora production يحتاج Token server.

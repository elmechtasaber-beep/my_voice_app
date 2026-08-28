# النسخة المربوطة مع Supabase

هذه النسخة هي أساس العمل الحالي.

## Supabase
- URL: https://kwlovnyznahfkyhvmyzv.supabase.co
- Publishable key: موجود في `supabase_client.py`
- كل عمليات تغيير الرصيد الحساسة تتم عبر RPC في قاعدة البيانات.

## ما تم إصلاحه
- الشحن لا يضيف كوينز مباشرة من الهاتف؛ ينشئ `pending recharge request` عبر `create_recharge_request`.
- مرجع الدفع يحفظ داخل `recharge_requests.metadata`.
- إرسال الهدية يستعمل RPC الذري `send_gift` ويخصم من المرسل ويضيف 33% للمستلم.
- سجل العمليات يستخدم الأعمدة الموجودة فعلياً في الـschema ولا يطلب `balance_after` غير الموجود.
- `approve_recharge` محصور بدور `service_role`.
- لا يوجد service_role key داخل التطبيق.

## Agora
App ID:
`0df15e97a5b7423bbb0090bf560c9177`

في الإنتاج يجب استعمال Agora Token قصير المدة من Backend/Edge Function وعدم وضع App Certificate داخل APK.

## مهم للشحن الحقيقي
`create_recharge_request` لا يمنح كوينز. بعد تحقق Backend من عملية الدفع، يتم استدعاء `approve_recharge` من بيئة موثوقة فقط.

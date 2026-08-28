# Backend Production Checklist

## 1. Recharge
- التطبيق ينشئ طلب شحن بحالة `pending` فقط.
- Backend يتحقق من عملية الدفع مع مزود الدفع قبل الموافقة.
- بعد التحقق يستدعي `public.approve_recharge(request_id, provider, provider_reference)` باستخدام service role.
- لا تستدعِ `approve_recharge` من APK.

## 2. Agora
- App ID: `0df15e97a5b7423bbb0090bf560c9177`
- خزّن `AGORA_APP_CERTIFICATE` كـ secret في Backend/Edge Function فقط.
- ولّد Token قصير المدة للـchannel المطلوب.
- لا تضع App Certificate في التطبيق.

## 3. Coins / gifts
- لا تسمح للعميل بتحديث `wallets.balance` مباشرة.
- استخدم `send_gift` لإرسال الهدايا.
- النسبة الحالية للمستلم: 33% من قيمة الهدية.

## 4. Fruit game (room-scoped)
- `place_fruit_bet` هو المسار الوحيد للرهان من التطبيق؛ الخصم من `wallets.balance` يتم داخل RPC بشكل ذري.
- `fruit_rounds` و`fruit_bets` و`fruit_round_winners` مرتبطة بـ `room_id` وتُرسل عبر Supabase Realtime.
- فتح الجولة وحسمها وصناعة النتيجة يجب أن يتم من Edge Function/Backend بصلاحية `service_role`، وليس من APK.
- كل جولة 30 ثانية، ثم يحسمها السيرفر ويبدأ الجولة التالية.
- السيرفر يختار الفاكهة الفائزة؛ التطبيق لا يرسل النتيجة ولا يستطيع تغييرها.
- يتم دفع أرباح كل الرهانات المطابقة، ثم نشر أعلى 3 فائزين حسب الرصيد بعد التسوية.
- لا تضع `service_role` key داخل التطبيق.

## 5. What is already wired in the project
- غرفة الصوت تمرر `room_id` إلى لعبة الفواكه، لذلك اللعبة ليست لعبة عامة منفصلة عن الغرفة.
- الرهان يُرسل فور ضغط الفاكهة إلى Supabase RPC، ولا يوجد خصم محلي من الرصيد.
- نتائج الجولة والرهانات والفائزين الثلاثة تُبث عبر Realtime.
- إذا لم توجد جولة مفتوحة من السيرفر، تظهر اللعبة في حالة انتظار بدل اختلاق جولة محلية.

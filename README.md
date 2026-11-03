# MEXC Mobile Scanner (Kivy + Buildozer)

مشروع Android مبني بـ Kivy، مستند إلى منطق فلاتر السوق والمؤشرات الفنية في نسخة PyQt5 المرفقة.

## ما الذي يعمل في هذه النسخة؟
- جلب أزواج MEXC Spot العامة وترتيبها حسب حجم التداول.
- فلاتر EMA 9/21/200 وRSI وMACD وVWAP وحجم التداول ودفتر الأوامر.
- شاشة هاتف عربية قابلة للتمرير.
- وضع محاكاة Paper: فتح صفقة افتراضية ومتابعة السعر وإغلاقها عند TP/SL أو يدويًا.
- حفظ الإعدادات وسجل المحاكاة محليًا باستخدام SQLite.

## تنبيه مهم عن نطاق التحويل
هذه نسخة Kivy أولية للهاتف وليست نقلًا حرفيًا لكل وظائف برنامج PyQt5. تم استبعاد إرسال أوامر BUY/SELL الحقيقية ومفاتيح API من نسخة الهاتف؛ لا يوجد فيها اتصال مصادق لتنفيذ تداول فعلي. النتائج والمؤشرات ليست توصية استثمارية، وقد تتأخر بيانات الشبكة أو تفشل.

## التشغيل على الكمبيوتر للاختبار
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## البناء إلى APK عبر Buildozer
Buildozer يعمل عادةً على Linux. أسهل طريقة هي GitHub Actions:
1. أنشئ مستودعًا جديدًا على GitHub.
2. ارفع محتويات هذا المجلد إلى الفرع `main`.
3. افتح تبويب **Actions**.
4. شغّل **Build Android APK** من زر **Run workflow**، أو ادفع Commit جديدًا.
5. بعد نجاح المهمة افتح نتيجة التشغيل ونزّل Artifact باسم `mexc-mobile-scanner-apk`.

للبناء المحلي على Ubuntu:
```bash
pip install buildozer cython==0.29.36
buildozer android debug
```

ملف APK الناتج يظهر داخل مجلد `bin/`.

## هيكل المشروع
- `main.py`: واجهة Kivy وإدارة الشاشة والمحاكاة.
- `scanner.py`: جلب بيانات السوق والمؤشرات والفلاتر العامة.
- `storage.py`: إعدادات SQLite وسجل الصفقات الافتراضية.
- `buildozer.spec`: إعدادات بناء Android.
- `.github/workflows/build-apk.yml`: بناء APK تلقائيًا.

## الترخيص
أضف الترخيص المناسب قبل النشر العام، وتأكد من الالتزام بشروط استخدام MEXC.

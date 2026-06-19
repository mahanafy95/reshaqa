export const metadata = {
  title: "سياسة الخصوصية — رشاقة",
  description: "سياسة خصوصية تطبيق رشاقة لحساب السعرات والتغذية",
};

const UPDATED = "يونيو 2026";
const CONTACT = "mahmoud.ha.hanafy@gmail.com";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-6">
      <h2 className="text-lg font-bold text-teal mb-2">{title}</h2>
      <div className="text-gray-700 leading-relaxed space-y-2">{children}</div>
    </section>
  );
}

export default function PrivacyPage() {
  return (
    <div dir="rtl" className="min-h-screen bg-soft py-10 px-4">
      <div className="max-w-2xl mx-auto bg-surface rounded-2xl shadow-sm p-6 md:p-8">
        <h1 className="text-2xl font-extrabold text-teal mb-1">سياسة الخصوصية — رشاقة 🥗</h1>
        <p className="text-muted text-sm mb-6">آخر تحديث: {UPDATED}</p>

        <Section title="مقدمة">
          <p>
            رشاقة تطبيق لحساب السعرات والتغذية يساعدك تتابع أكلك ووزنك وأهدافك الصحية.
            خصوصيتك تهمّنا، والصفحة دي بتوضّح إيه البيانات اللي بنجمعها وإزاي بنستخدمها.
          </p>
        </Section>

        <Section title="البيانات اللي بنجمعها">
          <ul className="list-disc pr-5 space-y-1">
            <li>بيانات الحساب: اسم المستخدم، والبريد الإلكتروني (اختياري — لاسترجاع كلمة السر أو الدخول بجوجل).</li>
            <li>بيانات الجسم والهدف: العمر، الجنس، الطول، الوزن، مستوى النشاط، الوزن المستهدف.</li>
            <li>سجلّاتك: الأكل، الوزن، المياه، الحالة المزاجية، والنشاط البدني.</li>
            <li>بيانات صحية اختيارية: لو فعّلت مزامنة الصحة (هواوي / Health Connect) — خطوات ودقائق نشاط وسعرات محروقة ونوم.</li>
            <li>معلومات الاشتراك: حالة اشتراكك في Premium (تتم إدارة الدفع بالكامل عبر Google Play — إحنا ما بنشوفش بيانات بطاقتك).</li>
          </ul>
        </Section>

        <Section title="إزاي بنستخدم البيانات">
          <p>
            بنستخدم بياناتك فقط لتشغيل التطبيق: حساب احتياجك من السعرات والماكروز، عرض تقدّمك
            وتقاريرك، وتذكيرك بأهدافك. ما بنبيعش بياناتك ولا بنستخدمها في إعلانات.
          </p>
        </Section>

        <Section title="مشاركة البيانات والخدمات الخارجية">
          <ul className="list-disc pr-5 space-y-1">
            <li>تسجيل الدخول بجوجل (Google Identity) — للتحقّق من هويتك عند اختيارك الدخول بجوجل.</li>
            <li>Google Play Billing — لإدارة الاشتراكات والدفع.</li>
            <li>مزوّدو الاستضافة (الخادم وقاعدة البيانات) لتخزين بياناتك بشكل آمن.</li>
          </ul>
          <p>ما بنشاركش بياناتك مع أي جهة تانية لأغراض تسويقية.</p>
        </Section>

        <Section title="تخزين البيانات وأمانها">
          <p>
            بياناتك بتتنقل عبر اتصال مشفّر (HTTPS) وبتتخزّن على خوادم آمنة، وكلمات السر بتتخزّن
            مشفّرة (hashing) ولا يمكن استرجاعها كنص.
          </p>
        </Section>

        <Section title="حذف حسابك وبياناتك">
          <p>
            تقدر تحذف حسابك وكل بياناتك نهائياً في أي وقت من داخل التطبيق:
            <span className="font-semibold"> الإعدادات ← حذف حسابي</span>، أو من صفحة{" "}
            <a href="/delete-account" className="text-teal underline">حذف الحساب</a>.
            أو راسلنا على البريد أدناه وهنحذفها خلال مدة قصيرة.
          </p>
        </Section>

        <Section title="الأطفال">
          <p>التطبيق غير موجّه للأطفال أقل من 13 سنة، ولا نجمع بياناتهم عن قصد.</p>
        </Section>

        <Section title="إخلاء مسؤولية طبي">
          <p>
            رشاقة أداة توعية ومساعدة، وليست بديلاً عن استشارة طبية أو تغذوية متخصّصة.
            استشر مختصاً قبل أي تغيير كبير في نظامك الغذائي.
          </p>
        </Section>

        <Section title="تعديلات على السياسة">
          <p>قد نحدّث السياسة من وقت لآخر، وهننشر أي تغييرات على الصفحة دي مع تاريخ التحديث.</p>
        </Section>

        <Section title="تواصل معنا">
          <p>
            لأي استفسار عن خصوصيتك أو لطلب حذف بياناتك:{" "}
            <a href={`mailto:${CONTACT}`} className="text-teal underline">{CONTACT}</a>
          </p>
        </Section>
      </div>
    </div>
  );
}

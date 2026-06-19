import type { Metadata } from "next";
import { Cairo } from "next/font/google";
import "./globals.css";

const cairo = Cairo({ subsets: ["arabic", "latin"], variable: "--font-cairo" });

export const metadata: Metadata = {
  title: "رشاقة — حاسبة السعرات والتغذية بالعربي",
  description:
    "تطبيق عربي بسيط لحساب السعرات وتتبّع الوزن مع مساعد ذكي — سجّل أكلك بالكلام أو الباركود، وحقّق هدفك الصحي.",
  applicationName: "رشاقة",
  keywords: ["سعرات", "تغذية", "تخسيس", "حمية", "وزن", "رشاقة", "حاسبة سعرات"],
  openGraph: {
    title: "رشاقة — حاسبة السعرات والتغذية بالعربي",
    description: "سجّل أكلك بسهولة، تابع وزنك، واستعن بمساعد ذكي يفهمك — مجاناً.",
    type: "website",
    locale: "ar_EG",
  },
};

export const viewport = {
  themeColor: "#1B998B",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl" className={cairo.variable}>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html:
              "(function(){try{var t=localStorage.getItem('theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme: dark)').matches)){document.documentElement.classList.add('dark');}}catch(e){}})();",
          }}
        />
      </head>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}

import type { Metadata } from "next";
import { Inter, Libre_Baskerville } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
});

const libreBaskerville = Libre_Baskerville({
  variable: "--font-libre-baskerville",
  subsets: ["latin"],
  weight: ["400", "700"],
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: "Aequitas Academic - Instructor Portal",
  description: "Secure Examination Environment",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} ${libreBaskerville.variable} antialiased min-h-screen flex flex-col`}
        suppressHydrationWarning
      >
        <div className="flex-1">{children}</div>
        <footer className="w-full py-3 text-center text-xs text-zinc-400 bg-zinc-50/80 border-t border-zinc-100">
          Built by{" "}
          <a
            href="https://www.linkedin.com/in/theaaryankapoor/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary-600 hover:text-primary-800 transition-colors duration-200 underline underline-offset-2"
          >
            Aaryan Kapoor
          </a>
        </footer>
      </body>
    </html>
  );
}

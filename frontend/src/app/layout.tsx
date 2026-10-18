import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { AccountProvider } from "@/components/account-provider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Quorum",
  description: "Group buying for furniture. The price drops as Members join.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-background text-foreground">
        <AccountProvider>{children}</AccountProvider>
      </body>
    </html>
  );
}

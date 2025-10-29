import type { Metadata } from "next";
import { Toaster } from "@/components/ui/toaster";
import "./globals.css";
import { TahoeLogo } from "@/app/images/logo";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Keep Tahoe Blue Data Collection",
  description: "Data collection form for the Keep Tahoe Blue initiative.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Lato:wght@400;700;900&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="font-body antialiased">
      <header className="absolute top-0 left-0 p-4">
          <Link href="/" className="flex items-center gap-2 text-primary">
              <TahoeLogo className="h-8 w-8" />
              <span className="sr-only">Home</span>
          </Link>
      </header>
        {children}
        <Toaster />
      </body>
    </html>
  );
}

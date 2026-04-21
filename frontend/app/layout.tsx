import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Software Distribution Platform",
  description: "Sell, license, update, and distribute desktop software securely."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

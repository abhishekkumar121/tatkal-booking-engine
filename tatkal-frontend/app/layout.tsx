import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tatkal Engine",
  description: "Flash-sale style Tatkal booking demo",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

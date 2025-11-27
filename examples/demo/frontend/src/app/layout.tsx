import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Odin Agent - Full Stack Demo",
  description: "Weather and Calendar assistant powered by Odin + CopilotKit",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}

import "./globals.css";
import { AuthProvider } from "@/lib/auth";

export const metadata = {
  title: "Factor",
  description: "Operations for solo Instagram and WhatsApp sellers",
};

export const viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}

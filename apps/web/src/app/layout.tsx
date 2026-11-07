import "./globals.css";

export const metadata = {
  title: "Factor",
  description: "Operations for solo Instagram and WhatsApp sellers",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

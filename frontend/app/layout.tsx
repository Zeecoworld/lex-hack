import "./globals.css";

export const metadata = {
  title: "AI Bias & Safety Auditor",
  description: "Audit LLM outputs for demographic disparity across decision scenarios",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

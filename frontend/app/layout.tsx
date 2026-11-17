import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Logccino | Agent-Native Big Data Intelligence',
  description: 'AI Agent-Native Big Data & Real-Time Intelligence Platform for Claude',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen flex flex-col">
        {children}
      </body>
    </html>
  );
}

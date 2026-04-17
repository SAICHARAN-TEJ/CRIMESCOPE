// app/layout.tsx — CRIMESCOPE Root Layout
import type { Metadata } from 'next';
import './globals.css';
import { Navbar }          from '@/components/shell/Navbar';
import { Sidebar }         from '@/components/shell/Sidebar';
import { StatusBar }       from '@/components/shell/StatusBar';
import { ScanlineOverlay } from '@/components/ui/ScanlineOverlay';

export const metadata: Metadata = {
  title: 'CRIMESCOPE — AI Crime Intelligence Platform',
  description: 'AI-powered crime intelligence and prediction platform. Multi-agent simulation, entity graph analysis, deep intelligence reports.',
  keywords: ['crime intelligence', 'AI simulation', 'forensics', 'law enforcement', 'predictive policing'],
  openGraph: {
    title: 'CRIMESCOPE — AI Crime Intelligence Platform',
    description: 'Swarm simulation meets crime intelligence. Now.',
    type: 'website',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap"
          rel="stylesheet"
        />
      </head>
      {/*
        body: full viewport, no body scroll — page-level scroll handled per-route.
        Main page has 600vh container inside a scrollable main.
      */}
      <body className="bg-[#080A0F] text-[#E8EAED] h-screen flex flex-col overflow-hidden">
        <ScanlineOverlay />
        <Navbar />
        <div className="flex flex-1 overflow-hidden" style={{ paddingTop: '56px' }}>
          <Sidebar />
          {/* main: scrollable — gives the 600vh hero its scroll space */}
          <main
            id="main-content"
            className="flex-1 overflow-y-auto relative"
            style={{ marginLeft: '64px', paddingBottom: '28px' }}
          >
            {children}
          </main>
        </div>
        <StatusBar />
      </body>
    </html>
  );
}

import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';
import { Toaster } from 'react-hot-toast';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Morphine Platform',
  description: 'Computer Vision-Powered Streaming Platform with Real-Time Analytics and Micro-Betting',
  keywords: 'streaming, computer vision, analytics, betting, real-time',
  authors: [{ name: 'Morphine Platform' }],
  creator: 'Morphine Platform',
  publisher: 'Morphine Platform',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://morphine.app',
    title: 'Morphine Platform',
    description: 'Computer Vision-Powered Streaming Platform with Real-Time Analytics and Micro-Betting',
    siteName: 'Morphine Platform',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Morphine Platform',
    description: 'Computer Vision-Powered Streaming Platform with Real-Time Analytics and Micro-Betting',
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          {children}
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#363636',
                color: '#fff',
              },
              success: {
                duration: 3000,
                iconTheme: {
                  primary: '#4ade80',
                  secondary: '#fff',
                },
              },
              error: {
                duration: 5000,
                iconTheme: {
                  primary: '#ef4444',
                  secondary: '#fff',
                },
              },
            }}
          />
        </Providers>
      </body>
    </html>
  );
} 
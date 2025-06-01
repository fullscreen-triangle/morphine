import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';
import { Toaster } from 'react-hot-toast';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Morphine - Revolutionary Universal Prediction & Expertise Economy Platform',
  description: 'The world\'s first Universal Human Knowledge Sharing Economy. Transform any live content into engaging multi-dimensional prediction experiences while creating transferable wealth from pure entertainment. Expert knowledge overlay system where any expert\'s insights can enhance any compatible video content globally.',
  keywords: 'universal predictions, expertise economy, knowledge overlay, annotation models, expert monetization, brand engagement revolution, social viewing, passive income, global education, streaming platform, computer vision, real-time analytics, collaborative intelligence',
  authors: [{ name: 'Morphine Revolutionary Platform' }],
  creator: 'Morphine Revolutionary Platform',
  publisher: 'Morphine Revolutionary Platform',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://morphine.app',
    title: 'Morphine - Revolutionary Universal Human Knowledge Sharing Economy',
    description: 'The world\'s first platform where human expertise becomes infinitely scalable digital assets, transforming every video into a potential masterclass while creating passive income streams for experts worldwide.',
    siteName: 'Morphine Revolutionary Platform',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Morphine - Universal Human Knowledge Sharing Economy',
    description: 'Revolutionary platform: Entertainment creates wealth, expertise becomes inheritance, knowledge becomes universally accessible. Any expert can create annotation models that enhance unlimited videos globally.',
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
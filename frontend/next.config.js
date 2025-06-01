/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  experimental: {
    appDir: true,
  },
  images: {
    domains: ['localhost', '127.0.0.1'],
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        source: '/api/core/:path*',
        destination: `${process.env.NEXT_PUBLIC_CORE_URL}/api/:path*`,
      },
      {
        source: '/api/analytics/:path*',
        destination: `${process.env.NEXT_PUBLIC_ANALYTICS_URL}/api/:path*`,
      },
    ];
  },
  webpack: (config) => {
    config.resolve.fallback = {
      ...config.resolve.fallback,
      fs: false,
      net: false,
      tls: false,
    };
    return config;
  },
};

module.exports = nextConfig; 
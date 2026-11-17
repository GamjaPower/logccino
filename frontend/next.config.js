/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*'
      },
      {
        source: '/sse',
        destination: 'http://localhost:8000/sse'
      }
    ];
  }
};

module.exports = nextConfig;

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/copilotkit',
        destination: 'http://localhost:8000/copilotkit',
      },
      {
        source: '/api/copilotkit/:path*',
        destination: 'http://localhost:8000/copilotkit/:path*',
      },
    ];
  },
};

export default nextConfig;

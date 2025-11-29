/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/copilotkit/:path*',
        destination: 'http://localhost:8000/copilotkit/:path*',
      },
    ];
  },
};

export default nextConfig;

/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ['192.168.1.171', 'localhost', 'odometrical-oiliest-livia.ngrok-free.dev'],
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://localhost:8001/api/v1/:path*',
      },
    ]
  },
};

export default nextConfig;

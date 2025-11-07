/** @type {import('next').NextConfig} */
const nextConfig = {
	async rewrites() {
		const backendOrigin =
			process.env.NEXT_PUBLIC_BACKEND_ORIGIN || "http://localhost:8000";
		return [
			{
				source: "/api/:path*",
				destination: `${backendOrigin}/api/:path*`,
			},
		];
	},
};

module.exports = nextConfig;

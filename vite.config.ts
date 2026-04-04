/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
	plugins: [react()],
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "./src"),
			"@app": path.resolve(__dirname, "./src/app"),
			"@modules": path.resolve(__dirname, "./src/modules"),
			"@shared": path.resolve(__dirname, "./src/shared"),
		},
	},
	test: {
		globals: true,
		environment: "jsdom",
		setupFiles: ["./src/test/setup.ts"],
		include: ["src/**/__tests__/**/*.test.{ts,tsx}", "src/**/*.test.{ts,tsx}"],
		coverage: {
			provider: "v8",
			reporter: ["text", "json", "html", "lcov"],
			exclude: ["node_modules/", "src/test/", "**/*.d.ts"],
		},
		css: false,
	},
	server: {
		host: "0.0.0.0",
		port: 7878,
		proxy: {
			"/api": {
				target: "http://localhost:7879",
				changeOrigin: true,
			},
			"/uploads": {
				target: "https://ucharmarket.uz",
				changeOrigin: true,
			},
		},
	},
	build: {
		outDir: "dist",
		sourcemap: true,
		rollupOptions: {
			output: {
				manualChunks: {
					vendor: ["react", "react-dom", "react-router-dom"],
					mantine: ["@mantine/core", "@mantine/hooks", "@mantine/form"],
					state: ["effector", "effector-react"],
					swiper: ["swiper"],
				},
			},
		},
	},
});

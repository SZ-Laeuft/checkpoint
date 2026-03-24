import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

const config = {
	preprocess: vitePreprocess(),
	kit: {
		paths: {
			base: '/static'
		},
		adapter: adapter()
	}
};

export default config;
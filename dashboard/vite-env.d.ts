// Mock definitions for Vite and plugins to satisfy IDE without npm install

declare module 'vite' {
    interface UserConfig {
        plugins?: any[];
        server?: {
            host?: string | boolean;
            port?: number;
            [key: string]: any;
        };
        [key: string]: any;
    }
    export function defineConfig(config: UserConfig): UserConfig;
}

declare module '@vitejs/plugin-react' {
    const plugin: () => any;
    export default plugin;
}

// Global JSX namespace for intrinsic elements (div, h1, etc.)
declare namespace JSX {
    interface IntrinsicElements {
        [elemName: string]: any;
    }
}

declare module 'react' {
    // Basic types
    type ReactNode = any;
    type FC<P = {}> = (props: P) => ReactNode;
    type FormEvent<T = any> = any;
    type ChangeEvent<T = any> = {
        target: {
            value: string;
            [key: string]: any;
        };
        preventDefault: () => void;
        [key: string]: any;
    };

    // Hooks
    function useState<T>(initialState: T | (() => T)): [T, (newState: T | ((prevState: T) => T)) => void];
    function useEffect(effect: () => void | (() => void), deps?: any[]): void;

    // Namespace for types if needed
    namespace React {
        type ReactNode = any;
        type FC<P = {}> = (props: P) => ReactNode;
        type FormEvent<T = any> = any;
        type ChangeEvent<T = any> = any;
    }

    // Exports
    export { useState, useEffect, FC, FormEvent, ChangeEvent, ReactNode };
    const React: any;
    export default React;
}

declare module 'react/jsx-runtime' {
    const _default: any;
    export default _default;
}

declare module 'recharts' {
    export const BarChart: any;
    export const Bar: any;
    export const LineChart: any;
    export const Line: any;
    export const PieChart: any;
    export const Pie: any;
    export const Cell: any;
    export const XAxis: any;
    export const YAxis: any;
    export const CartesianGrid: any;
    export const Tooltip: any;
    export const Legend: any;
    export const ResponsiveContainer: any;
}

declare module 'lucide-react' {
    export const Code: any;
    export const AlertTriangle: any;
    export const CheckCircle: any;
    export const TrendingUp: any;
    export const Upload: any;
    export const Settings: any;
    export const LogOut: any;
    export const User: any;
    export const Home: any;
    export const Activity: any;
}

// Added definitions for Vite and React 18
declare module 'react-dom/client' {
    export function createRoot(container: Element | DocumentFragment | null): {
        render(children: React.ReactNode): void;
        unmount(): void;
    };
}

declare module 'vite' {
    interface UserConfig {
        plugins?: any[];
        server?: {
            host?: string;
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

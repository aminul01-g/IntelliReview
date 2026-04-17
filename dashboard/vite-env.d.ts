/// <reference types="vite/client" />
// Mock definitions for Vite and plugins to satisfy IDE without npm install

declare module 'react' {
    export class Component<P = {}, S = {}, SS = any> {
        constructor(props: P);
        props: P;
        state: S;
        setState(state: S | ((prevState: S, props: P) => S), callback?: () => void): void;
        forceUpdate(callback?: () => void): void;
        render(): any;
        context: any;
        refs: any;
    }
    export function useState<T>(initialState: T | (() => T)): [T, (newState: T | ((curr: T) => T)) => void];
    export function useEffect(effect: () => void | (() => void), deps?: any[]): void;
    export function useReducer<R extends (state: any, action: any) => any, I>(
        reducer: R,
        initializerArg: I,
        initializer?: (arg: I) => any
    ): [any, any];
    export function useCallback<T extends (...args: any[]) => any>(callback: T, deps: any[]): T;
    export function useContext<T>(context: any): T;
    export function useRef<T>(initialValue: T): { current: T };
    export function useRef<T>(initialValue: T | null): { current: T | null };
    export function useRef<T = undefined>(): { current: T | undefined };
    export function useMemo<T>(factory: () => T, deps: any[] | undefined): T;
    export function createContext<T>(defaultValue: T): any;
    export const StrictMode: any;
    export interface ErrorInfo { componentStack: string; }
    export type ReactNode = any;
    export type DragEvent<T = any> = any;
    export type ChangeEvent<T = any> = any;
    export type FormEvent<T = any> = any;
    export interface HTMLAttributes<T> {
        [key: string]: any;
        webkitdirectory?: string | boolean;
    }
    export namespace React {
        export type DragEvent<T = any> = any;
        export type ChangeEvent<T = any> = any;
        export type FormEvent<T = any> = any;
        export type ReactNode = any;
    }
    const React: any;
    export default React;
}

declare module 'react-dom/client' {
    export function createRoot(container: Element | DocumentFragment): any;
}

declare module 'react-router-dom' {
    export function createBrowserRouter(routes: any[]): any;
    export const RouterProvider: any;
    export const Navigate: any;
    export const NavLink: any;
    export function useNavigate(): any;
    export function useParams<T = any>(): T;
    export function useLocation(): any;
    export const Link: any;
    export const Outlet: any;
}

declare module 'axios' {
    export interface AxiosResponse<T = any> { data: T; status: number; headers: any; config: any }
    export interface AxiosError<T = any> { response?: AxiosResponse<T>; config: any; message: string }
    export interface AxiosInstance {
        (config: any): Promise<AxiosResponse>;
        get<T = any>(url: string, config?: any): Promise<AxiosResponse<T>>;
        post<T = any>(url: string, data?: any, config?: any): Promise<AxiosResponse<T>>;
        put<T = any>(url: string, data?: any, config?: any): Promise<AxiosResponse<T>>;
        delete<T = any>(url: string, config?: any): Promise<AxiosResponse<T>>;
        patch<T = any>(url: string, data?: any, config?: any): Promise<AxiosResponse<T>>;
        create(config?: any): AxiosInstance;
        interceptors: {
            request: { use(onFulfilled: any, onRejected?: any): number; eject(id: number): void };
            response: { use(onFulfilled: any, onRejected?: any): number; eject(id: number): void };
        };
    }
    const axios: AxiosInstance;
    export default axios;
}

declare module 'lucide-react' {
    export const Activity: any;
    export const Clock: any;
    export const ShieldAlert: any;
    export const GitMerge: any;
    export const FileCode: any;
    export const Play: any;
    export const AlertCircle: any;
    export const CheckCircle: any;
    export const Check: any;
    export const X: any;
    export const ShieldWarning: any;
    export const Search: any;
    export const Settings: any;
    export const User: any;
    export const LogOut: any;
    export const LayoutDashboard: any;
    export const History: any;
    export const BarChart3: any;
    export const Plus: any;
    export const Shield: any;
    export const ArrowRight: any;
    export const ShieldCheck: any;
    export const Zap: any;
    export const Code: any;
    export const Upload: any;
    export const UploadCloud: any;
    export const FileText: any;
    export const RefreshCw: any;
    export const GitBranch: any;
    export const Users: any;
    export const TrendingDown: any;
    export const Bell: any;
    export const Key: any;
    export const Github: any;
}

declare module 'recharts' {
    export const ResponsiveContainer: any;
    export const LineChart: any;
    export const Line: any;
    export const BarChart: any;
    export const Bar: any;
    export const PieChart: any;
    export const Pie: any;
    export const Cell: any;
    export const XAxis: any;
    export const YAxis: any;
    export const CartesianGrid: any;
    export const Tooltip: any;
    export const Legend: any;
    export const AreaChart: any;
    export const Area: any;
}

declare module '@tanstack/react-query' {
    export const QueryClient: any;
    export const QueryClientProvider: any;
    export function useQuery<T = any>(options: any): any;
    export function useMutation<T = any>(options: any): any;
}

declare module '@tanstack/react-table' {
    export function createColumnHelper<T = any>(): any;
    export const flexRender: any;
    export const getCoreRowModel: any;
    export function useReactTable(options: any): any;
}

declare module '@radix-ui/react-dialog' {
    export const Root: any;
    export const Portal: any;
    export const Overlay: any;
    export const Content: any;
    export const Title: any;
    export const Description: any;
    export const Close: any;
}

declare module '@monaco-editor/react' {
    const Editor: any;
    export default Editor;
}

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

declare module 'tailwind-merge' {
    export function twMerge(...args: any[]): string;
}


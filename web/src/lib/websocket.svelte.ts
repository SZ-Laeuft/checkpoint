export interface UserData {
    id: number | null;
    name: string;
    surname: string;
    best_time: number;
    lap_count: number;
    round_time: number;
}
const initialState: UserData = {
    id: null,
    name: '',
    surname: '',
    best_time: 0,
    lap_count: 0,
    round_time: 0
};

export let user: UserData = $state(initialState);

// Configuration
const MAX_RECONNECT_DELAY = 30000; // set maximum cap of delay to 30 seconds
const BASE_RECONNECT_DELAY = 1000;
const HEARTBEAT_INTERVAL = 5000;
const PING_TIMEOUT = 1000;

let socket: WebSocket | null = null;
let reconnectTimeout: ReturnType<typeof setTimeout>;
let clearUserTimeout: ReturnType<typeof setTimeout>;
let heartbeatInterval: ReturnType<typeof setInterval>;
let pingTimeout: ReturnType<typeof setTimeout>;

let reconnectAttempts = 0;
let isIntentionalClose = false;

export function getWebSocketState(): boolean {
    return socket?.readyState === WebSocket.OPEN;
}

export function connectWebSocket(url: string) {
    console.log("WebSocket service started for:", url);
    isIntentionalClose = false;

    function setupHeartbeat() {
        clearInterval(heartbeatInterval);
        heartbeatInterval = setInterval(() => {
            if (!socket || socket.readyState !== WebSocket.OPEN) return;

            console.log("Sending Heartbeat...");
            socket.send(JSON.stringify({ type: 'ping' })); // Adjust based on your server protocol

            // If we don't get a response/message in time, kill it
            clearTimeout(pingTimeout);
            pingTimeout = setTimeout(() => {
                console.warn("Heartbeat timed out. Closing socket.");
                socket?.close();
            }, PING_TIMEOUT);
        }, HEARTBEAT_INTERVAL);
    }

    function connect() {
        // If we are already connected or connecting, do nothing
        if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
            return;
        }

        console.log(`Attempting connection (Attempt ${reconnectAttempts + 1})...`);

        socket = new WebSocket(url);

        socket.onopen = () => {
            console.log('WebSocket connected');
            reconnectAttempts = 0; // Reset backoff on success
            setupHeartbeat();
        };

        socket.onmessage = (event) => {
            clearTimeout(pingTimeout);
            console.log("WS message:", event.data);
            try {
                const data = JSON.parse(event.data);

                // Keepalive
                if (data?.type === 'pong') return;

                // Accept payloads based on presence of id, not truthiness of all fields
                if (typeof data?.id === 'number') {
                    user.id = data.id;
                    user.name = typeof data.name === 'string' ? data.name : '';
                    user.surname = typeof data.surname === 'string' ? data.surname : '';
                    user.best_time = typeof data.best_time === 'number' ? data.best_time : 0;
                    user.lap_count = typeof data.lap_count === 'number' ? data.lap_count : 0;
                    user.round_time = typeof data.round_time === 'number' ? data.round_time : 0;
                    
                    // Always restart clear timer on each scan
                    clearTimeout(clearUserTimeout);
                    const currentId = user.id;
                    clearUserTimeout = setTimeout(() => {
                        // Prevent stale timeout from clearing newer user data
                        if (user.id === currentId) {
                            Object.assign(user, initialState);
                        }
                    }, currentId === -1 ? 10000 : 6000);
                }
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };


        socket.onclose = (event) => {
            clearInterval(heartbeatInterval);
            clearTimeout(pingTimeout);

            if (isIntentionalClose) return;

            // Calculate exponential backoff with jitter
            // Math.min(30s, 1000 * 2^attempts)
            const delay = Math.min(
                MAX_RECONNECT_DELAY,
                (BASE_RECONNECT_DELAY * Math.pow(2, reconnectAttempts)) + (Math.random() * 1000)
            );

            console.log(`WebSocket disconnected. Reconnecting in ${Math.round(delay)}ms...`);

            reconnectTimeout = setTimeout(() => {
                reconnectAttempts++;
                connect();
            }, delay);
        };

        socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            // Verify state is OPEN before trying to close, otherwise onclose fires automatically
            if (socket?.readyState === WebSocket.OPEN) {
                socket.close();
            }
        };
    }

    // Initial connection
    connect();

    // Return cleanup function for Svelte lifecycle
    return () => {
        isIntentionalClose = true;

        if (socket) {
            socket.onclose = null;
            socket.onmessage = null;
            socket.onerror = null;
            socket.close();
        }

        clearTimeout(reconnectTimeout);
        clearTimeout(clearUserTimeout);
        clearInterval(heartbeatInterval);
        clearTimeout(pingTimeout);
    };
}
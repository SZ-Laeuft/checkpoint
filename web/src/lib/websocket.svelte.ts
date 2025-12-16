import { writable } from 'svelte/store';
import { setContext } from "svelte";

export interface UserData {
    id: number | null;
    name: string;
    surname: string;
}

const initialState: UserData = {
    id: null,
    name: '',
    surname: '',
};

export let user: UserData = $state(initialState);
let socket: WebSocket | null = null;
let reconnectTimeout: ReturnType<typeof setTimeout>;
let clearUserTimeout: ReturnType<typeof setTimeout>;

export function getWebSocketState(): boolean {
    return socket?.readyState === WebSocket.OPEN;
}
export function connectWebSocket(url: string) {
    console.log("Websocket connecting to:", url);

    function connect() {
        // Close existing connection if any
        if (socket) {
            socket.close();
        }

        socket = new WebSocket(url);

        socket.onopen = () => {
            console.log('WebSocket connected');
            clearTimeout(reconnectTimeout);
        };

        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.id && data.name && data.surname) {
                    user.id = data.id;
                    user.name = data.name;
                    user.surname = data.surname;

                    // Reset the timeout whenever new data is received
                    clearTimeout(clearUserTimeout); // Clear the existing timeout
                    clearUserTimeout = setTimeout(() => {
                        if (user.id === data.id) { // Double-check current user ID matches to avoid race conditions
                            user.id = null;
                            user.name = '';
                            user.surname = '';
                        }
                    }, (user.id === -1 ? 10000 : 6000)); // Use the appropriate timeout duration
                }
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };

        socket.onclose = () => {
            console.log('WebSocket disconnected. Reconnecting in 3s...');
            // Attempt to reconnect
            reconnectTimeout = setTimeout(connect, 3000);
        };

        socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            socket?.close(); // Trigger onclose to handle reconnect
        };
    }

    connect();

    // Return a cleanup function
    return () => {
        if (socket) {
            socket.onclose = null;
            socket.close();
        }
        clearTimeout(reconnectTimeout);
        clearTimeout(clearUserTimeout);
    };
}
import { writable } from 'svelte/store';
import {setContext} from "svelte";

interface UserData {
    id: string | null;
    name: string;
    surname: string;
}

const initialState: UserData = {
    id: null,
    name: '',
    surname: '',
};

let socket: WebSocket | null = null;
let reconnectTimeout: ReturnType<typeof setTimeout>;

export function connectWebSocket(url: string) {
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
                // Validate we received the expected fields
                if (data.id && data.name && data.surname) {
                    setContext("user", () => ({
                        id: data.id,
                        name: data.name,
                        surname: data.surname
                    }));
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
            // Remove listener to prevent auto-reconnect on manual cleanup
            socket.onclose = null;
            socket.close();
        }
        clearTimeout(reconnectTimeout);
    };
}
import { writable } from 'svelte/store';
import {setContext} from "svelte";

export interface UserData {
    id: string | null;
    name: string;
    surname: string;
}

const initialState: UserData = {
    id: null,
    name: '',
    surname: '',
};
export let user: UserData = $state(initialState)
let socket: WebSocket | null = null;
let reconnectTimeout: ReturnType<typeof setTimeout>;

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

                    // clear user data after 6 seconds, if it hasn't changed
                    setTimeout((id: string | null = user.id) => {
                        if (id === user.id) {
                        user.id = null;
                        user.name = '';
                        user.surname = '';
                        }
                    }, 6000);
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
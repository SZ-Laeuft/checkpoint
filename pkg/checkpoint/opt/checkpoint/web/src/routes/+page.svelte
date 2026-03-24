<script lang="ts">
    import { getContext, onMount } from 'svelte';
    import {connectWebSocket, type UserData, user, getWebSocketState} from '$lib/websocket.svelte';
    import { PUBLIC_SERVER_API_URL } from "$env/static/public";
    let time = $state(new Date());
    let socketError: boolean = $state(true);
    onMount(() => {
        const cleanup = connectWebSocket(PUBLIC_SERVER_API_URL);
        const interval = setInterval(() => {
            time = new Date();
            socketError = getWebSocketState();
        }, 1000);

        return () => {
            cleanup();
            clearInterval(interval);

        };
    });

    function formatTime(date: Date): string {
        return pad(date.getHours()) + ':' + pad(date.getMinutes()) + ':' + pad(date.getSeconds());
    }
    function pad(num: number): string {
        return num.toString().padStart(2, '0');
    }
</script>

<div class="absolute top-0 right-0 m-1 text-[0.4em] {user.id === null ? 'text-black' : 'text-white'}">
    {socketError ? null : "Verbindung zu Checkpoint Core unterbrochen! - "} {formatTime(time)}
</div>
<main class="flex items-center content-evenly justify-center w-full h-screen">
    {#if user.id === null}
        <p class="text-center">Bereit zum Scannen!</p>
        {:else if user.id === -1}
        <div class="w-screen h-screen flex flex-col items-center justify-center gap-4
            bg-red-600 text-white p-4">
            <p class="text-center text-5xl">Fehler!</p>
            <p class="text-center text-xs">Melde dich bei den Veranstaltern!</p>
        </div>
    {:else}
        <div class="w-screen h-screen text-white flex flex-col items-center justify-center gap-4 bg-green-600 p-4">
            <ol>
                <li>{user.name} {user.surname}</li>
                <div class="text-[0.7em]">
                    <li>Rundenanzahl: {user.lap_count}</li>
                    <li>Bestzeit: {user.best_time}</li>
                </div>
            </ol>
        </div>
    {/if}
</main>
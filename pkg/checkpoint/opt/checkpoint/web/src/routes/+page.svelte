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
    function pad(n: number, z: number = 2): string {
        z = z || 2;
        return ('00' + n).slice(-z);
    }
    function msToTime(seconds: number): string {
        if (!Number.isFinite(seconds)) return '--:--';

        const msTotal = Math.round(seconds * 1000);
        const hrs = Math.floor(msTotal / 3600000);
        const mins = Math.floor((msTotal % 3600000) / 60000);
        const secs = Math.floor((msTotal % 60000) / 1000);

        if (hrs > 0) {
            return `${pad(hrs)}:${pad(mins)}:${pad(secs)}`;
        }

        return `${pad(mins)}:${pad(secs)}`;
    }
    function formatTime(date: Date): string {
        return pad(date.getHours()) + ':' + pad(date.getMinutes()) + ':' + pad(date.getSeconds());
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
                    <li>Bestzeit: {msToTime(user.best_time)}</li>
                    <li>Rundenzeit: {msToTime(user.round_time)}</li>
                </div>
            </ol>
        </div>
    {/if}
</main>
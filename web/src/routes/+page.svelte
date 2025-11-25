<script lang="ts">
    import {getContext, onMount} from 'svelte';
    import { connectWebSocket } from '$lib/websocketStore';
    let user = getContext("user")
    onMount(() => {
        // Replace with your actual WebSocket URL
        const cleanup = connectWebSocket('ws://localhost:8000/ws');

        return () => {
            cleanup();
        };
    });
</script>
oida:
{user}

<div class="min-h-screen flex items-center justify-center bg-slate-50 p-6">
    Servas
</div>
<script lang="ts">
    import type {UserData} from "$lib/websocket.svelte";

    let props = $props();
</script>

<ol>
    <li>{props.user.id}</li>
    <li>{props.user.surname}</li>
    <li>{props.user.name}</li>
</ol>
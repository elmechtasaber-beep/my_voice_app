import asyncio
import inspect
import threading


def subscribe_postgres(channel, event, schema, table, callback, filter_value=None):
    """Subscribe using current supabase-py API, while staying compatible with sync/async returns."""
    kwargs = {
        "event": event,
        "schema": schema,
        "table": table,
        "callback": callback,
    }
    if filter_value:
        kwargs["filter"] = filter_value

    channel.on_postgres_changes(**kwargs)
    result = channel.subscribe()
    if inspect.isawaitable(result):
        _run_awaitable(result)
    return channel


def _run_awaitable(awaitable):
    def runner():
        try:
            asyncio.run(awaitable)
        except Exception as exc:
            print(f"Realtime subscription error: {exc}")

    threading.Thread(target=runner, daemon=True).start()


def unsubscribe_channel(channel):
    if not channel:
        return
    try:
        result = channel.unsubscribe()
        if inspect.isawaitable(result):
            _run_awaitable(result)
    except Exception as exc:
        print(f"Realtime unsubscribe error: {exc}")

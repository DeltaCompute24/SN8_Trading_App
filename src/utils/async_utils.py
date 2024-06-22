import anyio

def run_async_in_sync(func, *args, **kwargs):
    try:
        return anyio.run(func, *args, **kwargs)
    except RuntimeError:
        # Handles case where there is already an existing event loop
        import asyncio
        return asyncio.run(func(*args, **kwargs))

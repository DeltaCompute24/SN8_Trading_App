import anyio
import asyncio


# def run_async_in_sync(func, *args, **kwargs):
#     try:
#         return anyio.run(func, *args, **kwargs)
#     except RuntimeError:
#         # Handles case where there is already an existing event loop
#         import asyncio
#         return asyncio.run(func(*args, **kwargs))

def run_async_in_sync(async_func, *args, **kwargs):
    """
    Run an async function in a synchronous context.

    Parameters:
    async_func: The async function to run.
    *args, **kwargs: Arguments and keyword arguments to pass to the async function.

    Returns:
    The result of the async function.
    """
    loop = asyncio.new_event_loop()  # Create a new event loop
    asyncio.set_event_loop(loop)  # Set the new loop as the current event loop
    try:
        return loop.run_until_complete(async_func(*args, **kwargs))  # Run the async function
    finally:
        loop.close()  # Close the event loop after execution

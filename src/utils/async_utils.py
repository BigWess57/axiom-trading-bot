import asyncio

def bridge_callback(coro_func):
    """
    Bridge callback to wrap coroutine functions.
    Allows passing async functions to synchronous callbacks by scheduling them as tasks.
    """
    def wrapper(*args, **kwargs):
        asyncio.create_task(coro_func(*args, **kwargs))
    return wrapper

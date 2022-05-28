import asyncio
import time

class TurnTimer:
    
    def __init__(self, timeout, callback):
        self._timeout = timeout
        self._callback = callback
        self._running = True
        self._endpoint = time.time() + timeout
        self._task = asyncio.ensure_future(self._job())
    
    def __bool__(self) -> bool:
        return self._running
    
    @property
    def time_left(self):
        return int(self._endpoint - time.time())
    
    async def _job(self):
        await asyncio.sleep(self._timeout)
        await self._callback()
        
    def cancel(self):
        self._running = False
        self._task.cancel()
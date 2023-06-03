from typing import Optional
from threading import Lock, Thread, BoundedSemaphore
from time import sleep
from collections import deque
from contextlib import AbstractContextManager


class TokenBucketRateLimiter(AbstractContextManager):
    """Rate limiter implementing the token bucket algorithm"""

    REFILL_SPACING_SECONDS: int
    MAX_TOKENS: int

    bucket: BoundedSemaphore = None
    queue: deque[Lock] = None
    queue_lock: Lock = None

    # Protect the number of tokens behind a lock
    __n_tokens_lock: Lock = None
    __n_tokens = 0

    @property
    def n_tokens(self):
        with self.__n_tokens_lock:
            return self.__n_tokens

    @n_tokens.setter
    def n_tokens(self, value: int):
        with self.__n_tokens_lock:
            self.n_tokens = value

    def __init__(
        self,
        refill_spacing_seconds: Optional[int] = None,
        max_tokens: Optional[int] = None,
        initial_tokens: Optional[int] = None,
    ) -> None:
        # Initialize default values
        self.queue_lock = Lock()
        if max_tokens is not None:
            self.MAX_TOKENS = max_tokens
        if refill_spacing_seconds is not None:
            self.REFILL_SPACING_SECONDS = refill_spacing_seconds

        # Initialize the bucket
        self.bucket = BoundedSemaphore(self.MAX_TOKENS)
        missing = 0 if initial_tokens is None else self.MAX_TOKENS - initial_tokens
        missing = max(0, min(missing, self.MAX_TOKENS))
        for _ in range(missing):
            self.bucket.acquire()

        # Initialize the counter
        self.__n_tokens_lock = Lock()
        self.n_tokens = self.MAX_TOKENS - missing

        # Spawn daemon thread that refills the bucket
        refill_thread = Thread(target=self.refill_thread_func, daemon=True)
        refill_thread.start()

    def refill(self):
        """Method used by the refill thread"""
        sleep(self.REFILL_SPACING_SECONDS)
        try:
            self.bucket.release()
        except ValueError:
            # Bucket was full
            pass
        else:
            self.n_tokens += 1
            self.update_queue()

    def refill_thread_func(self):
        """Entry point for the daemon thread that is refilling the bucket"""
        while True:
            self.refill()

    def update_queue(self) -> None:
        """Update the queue, moving it forward if possible. Non-blocking."""
        update_thread = Thread(target=self.queue_update_thread_func, daemon=True)
        update_thread.start()

    def queue_update_thread_func(self) -> None:
        """Queue-updating thread's entry point"""
        with self.queue_lock:
            if len(self.queue) == 0:
                return
            self.bucket.acquire()
            self.n_tokens -= 1
            lock = self.queue.pop()
            lock.release()

    def add_to_queue(self) -> Lock:
        """Create a lock, add it to the queue and return it"""
        lock = Lock()
        lock.acquire()
        with self.queue_lock:
            self.queue.appendleft(lock)
        return lock

    def acquire(self):
        """Acquires a token from the bucket when it's your turn in queue"""
        lock = self.add_to_queue()
        self.update_queue()
        lock.acquire()

    # --- Support for use in with statements

    def __enter__(self):
        self.acquire()

    def __exit__(self, *_args):
        pass

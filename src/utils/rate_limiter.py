from threading import Lock, Thread
from time import time_ns, sleep
from collections import deque
from contextlib import AbstractContextManager


class RateLimiter(AbstractContextManager):
    """
    Thread-safe and blocking rate limiter.

    There are at most X tokens available in the limiter, acquiring removes one
    and releasing gives back one.

    Acquire will block until those conditions are met:
    - There is a token available
    - At least Y nanoseconds have passed since the last token was acquired

    The order in which tokens are requested is the order in which they will be given.
    Works on a FIFO model.

    Can be used in a `with` statement like `threading.Lock`
    [Using locks, conditions, and semaphores in the with statement](https://docs.python.org/3/library/threading.html#using-locks-conditions-and-semaphores-in-the-with-statement)
    """

    # Number of tokens available in the limiter
    # = Max number of cuncurrent operations allowed
    MAX_TOKENS: int
    available_tokens: int = 0
    tokens_lock: Lock = None

    # Minimum time elapsed between two token being distributed
    # = Rate limit
    PICK_SPACING_NS: int
    last_pick_time: int = 0
    last_pick_time_lock: Lock = None

    # Queue containing locks unlocked when a token can be acquired
    # Doesn't need a thread lock, deques have thread-safe append and pop on both ends
    queue: deque[Lock] = None

    def __init__(self, pick_spacing_ns: int, max_tokens: int) -> None:
        self.PICK_SPACING_NS = pick_spacing_ns
        self.MAX_TOKENS = max_tokens
        self.last_pick_time = 0
        self.last_pick_time_lock = Lock()
        self.queue = deque()
        self.available_tokens = max_tokens
        self.tokens_lock = Lock()

    def update_queue(self) -> None:
        """
        Move the queue forward if possible.
        Non-blocking, logic runs in a daemon thread.
        """
        thread = Thread(target=self.queue_update_thread_func, daemon=True)
        thread.start()

    def queue_update_thread_func(self) -> None:
        """Queue-updating thread's entry point"""

        # Consume a token, if none is available do nothing
        with self.tokens_lock:
            if self.available_tokens == 0:
                return
            self.available_tokens -= 1

        # Get the next lock in queue, if none is available do nothing
        try:
            lock = self.queue.pop()
        except IndexError:
            return

        # Satisfy the minimum pick spacing
        with self.last_pick_time_lock:
            elapsed = time_ns() - self.last_pick_time
            if (ns_to_sleep := self.PICK_SPACING_NS - elapsed) > 0:
                sleep(ns_to_sleep / 10**9)
            self.last_pick_time = time_ns()

        # Finally unlock the acquire call linked to that lock
        lock.release()

    def add_to_queue(self) -> Lock:
        """Create a lock, add it to the queue and return it"""
        lock = Lock()
        lock.acquire()
        self.queue.appendleft(lock)
        return lock

    def acquire(self) -> None:
        """Pick a token from the limiter"""

        # Wait our turn in queue
        lock = self.add_to_queue()
        self.update_queue()

        # Block until lock is released (= its turn in queue)
        # Single-use (this call to acquire), so no need to release it
        lock.acquire()
        del lock

    def release(self) -> None:
        """Return a token to the limiter"""
        with self.tokens_lock:
            self.available_tokens += 1
        self.update_queue()

    # --- Support for use in with statements

    def __enter__(self):
        self.acquire()

    def __exit__(self):
        self.release()

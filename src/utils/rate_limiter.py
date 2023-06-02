from threading import Lock, Thread
from time import time_ns, sleep


class RateLimiter:
    """
    Thread-safe and blocking rate limiter.
    * There are at most X tokens available in the limiter
    * Tokens can't be picked faster than every Y nanoseconds
    * Acquire will block until those conditions are met
    * The first to request a token will also be the first to acquire one
    """

    PICK_SPACING_NS: float
    MAX_TOKENS: int

    _last_pick_time: int = 0
    _n_tokens: int = 0
    _queue: list[Lock] = None
    _queue_lock: Lock = None
    _tokens_lock: Lock = None
    _last_pick_time_lock: Lock = None

    def __init__(self, pick_spacing_ns: float, max_tokens: int) -> None:
        self.PICK_SPACING_NS = pick_spacing_ns
        self.MAX_TOKENS = max_tokens
        self._last_pick_time = 0
        self._last_pick_time_lock = Lock()
        self._queue = []
        self._queue_lock = Lock()
        self._n_tokens = max_tokens
        self._tokens_lock = Lock()

    def update_queue(self) -> None:
        """
        Move the queue forward if possible.
        Non-blocking, logic runs in a daemon thread.
        """
        thread = Thread(target=self.queue_update_thread_func, daemon=True)
        thread.start()

    def queue_update_thread_func(self) -> None:
        """Queue-updating thread's entry point"""
        with self._queue_lock, self._tokens_lock:
            # Unlock as many locks in the queue as there are tokens available
            n_unlocked = min(len(self._queue), self._n_tokens)
            for _ in range(n_unlocked):
                lock = self._queue.pop(0)
                lock.release()
            # Consume the tokens used
            self._n_tokens -= n_unlocked

    def add_to_queue(self) -> Lock:
        """Create a lock, add it to the queue and return it"""
        lock = Lock()
        lock.acquire()
        with self._queue_lock:
            self._queue.append(lock)
        return lock

    def acquire(self) -> None:
        """
        Pick a token from the limiter.
        Will block:
        * Until your turn in queue
        * Until the minimum pick spacing is satified
        """

        # Wait our turn in queue
        # (no need for with since queue locks are unique, will be destroyed after that)
        lock = self.add_to_queue()
        self.update_queue()
        lock.acquire()

        # TODO move to queue unlock (else order is not ensured)
        # Satisfy the minimum pick spacing
        now = time_ns()
        with self._last_pick_time_lock:
            elapsed = now - self._last_pick_time
            ns_to_sleep = self.PICK_SPACING_NS - elapsed
            self._last_pick_time = now
            if ns_to_sleep > 0:
                sleep(ns_to_sleep / 10**9)
                self._last_pick_time += ns_to_sleep

    def release(self) -> None:
        """Return a token to the bucket"""
        with self._tokens_lock:
            self._n_tokens += 1
        self.update_queue()

from typing import Optional, Sized
from threading import Lock, Thread, BoundedSemaphore
from time import sleep, time
from collections import deque
from contextlib import AbstractContextManager


class PickHistory(Sized):
    """Utility class used for rate limiters, counting how many picks
    happened in a given period"""

    PERIOD: int

    timestamps: list[int] = None
    timestamps_lock: Lock = None

    def __init__(self, period: int) -> None:
        self.PERIOD = period
        self.timestamps = []
        self.timestamps_lock = Lock()

    def remove_old_entries(self):
        """Remove history entries older than the period"""
        now = time()
        cutoff = now - self.PERIOD
        with self.timestamps_lock:
            self.timestamps = [entry for entry in self.timestamps if entry > cutoff]

    def add(self, *new_timestamps: Optional[int]):
        """Add timestamps to the history.
        If none given, will add the current timestamp"""
        if len(new_timestamps) == 0:
            new_timestamps = (time(),)
        with self.timestamps_lock:
            self.timestamps.extend(new_timestamps)

    def __len__(self) -> int:
        """How many entries were logged in the period"""
        self.remove_old_entries()
        with self.timestamps_lock:
            return len(self.timestamps)

    @property
    def start(self) -> int:
        """Get the time at which the history started"""
        self.remove_old_entries()
        with self.timestamps_lock:
            try:
                entry = self.timestamps[0]
            except IndexError:
                entry = time()
        return entry

    def copy_timestamps(self) -> str:
        """Get a copy of the timestamps history"""
        self.remove_old_entries()
        with self.timestamps_lock:
            return self.timestamps.copy()


class RateLimiter(AbstractContextManager):
    """Rate limiter implementing the token bucket algorithm"""

    # Period in which we have a max amount of tokens
    REFILL_PERIOD_SECONDS: int
    # Number of tokens allowed in this period
    REFILL_PERIOD_TOKENS: int
    # Max number of tokens that can be consumed instantly
    BURST_TOKENS: int

    pick_history: PickHistory = None
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
            self.__n_tokens = value

    def __init__(
        self,
        refill_period_seconds: Optional[int] = None,
        refill_period_tokens: Optional[int] = None,
        burst_tokens: Optional[int] = None,
    ) -> None:
        """Initialize the limiter"""

        # Initialize default values
        if refill_period_seconds is not None:
            self.REFILL_PERIOD_SECONDS = refill_period_seconds
        if refill_period_tokens is not None:
            self.REFILL_PERIOD_TOKENS = refill_period_tokens
        if burst_tokens is not None:
            self.BURST_TOKENS = burst_tokens
        if self.pick_history is None:
            self.pick_history = PickHistory(self.REFILL_PERIOD_SECONDS)

        # Create synchronization data
        self.__n_tokens_lock = Lock()
        self.queue_lock = Lock()
        self.queue = deque()

        # Initialize the token bucket
        self.bucket = BoundedSemaphore(self.BURST_TOKENS)
        self.n_tokens = self.BURST_TOKENS

        # Spawn daemon thread that refills the bucket
        refill_thread = Thread(target=self.refill_thread_func, daemon=True)
        refill_thread.start()

    @property
    def refill_spacing(self) -> float:
        """
        Get the current refill spacing.

        Ensures that even with a burst in the period, the limit will not be exceeded.
        """

        # Compute ideal spacing
        tokens_left = self.REFILL_PERIOD_TOKENS - len(self.pick_history)
        seconds_left = self.pick_history.start + self.REFILL_PERIOD_SECONDS - time()
        try:
            spacing_seconds = seconds_left / tokens_left
        except ZeroDivisionError:
            # There were no remaining tokens, gotta wait until end of the period
            spacing_seconds = seconds_left

        # Prevent spacing dropping down lower than the natural spacing
        natural_spacing = self.REFILL_PERIOD_SECONDS / self.REFILL_PERIOD_TOKENS
        return max(natural_spacing, spacing_seconds)

    def refill(self):
        """Add a token back in the bucket"""
        sleep(self.refill_spacing)
        try:
            self.bucket.release()
        except ValueError:
            # Bucket was full
            pass
        else:
            self.n_tokens += 1

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
        self.pick_history.add()

    # --- Support for use in with statements

    def __enter__(self):
        self.acquire()

    def __exit__(self, *_args):
        pass

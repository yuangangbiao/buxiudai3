"""熔断器——CLOSED→OPEN→HALF_OPEN 三态"""
import time
import threading
import logging

logger = logging.getLogger(__name__)

class CircuitBreaker:
    CLOSED = 'closed'
    OPEN = 'open'
    HALF_OPEN = 'half_open'

    def __init__(self, name, failure_threshold=5, timeout=30, success_threshold=2):
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        self._state = self.CLOSED
        self._failures = 0
        self._successes = 0
        self._last_failure_time = 0
        self._lock = threading.Lock()

    @property
    def state(self):
        return self._state

    def call(self, func, *args, **kwargs):
        with self._lock:
            if self._state == self.OPEN:
                if time.time() - self._last_failure_time >= self.timeout:
                    self._state = self.HALF_OPEN
                    self._successes = 0
                    logger.info(f"[熔断器] {self.name}: OPEN→HALF_OPEN")
                else:
                    raise CircuitBreakerOpenError(f"[{self.name}] 熔断中，拒绝请求")

        try:
            result = func(*args, **kwargs)
            with self._lock:
                if self._state == self.HALF_OPEN:
                    self._successes += 1
                    if self._successes >= self.success_threshold:
                        self._state = self.CLOSED
                        self._failures = 0
                        logger.info(f"[熔断器] {self.name}: HALF_OPEN→CLOSED")
                else:
                    self._failures = 0
            return result
        except Exception as e:
            with self._lock:
                self._failures += 1
                self._last_failure_time = time.time()
                if self._state == self.HALF_OPEN:
                    self._state = self.OPEN
                    logger.error(f"[熔断器] {self.name}: HALF_OPEN→OPEN (探测调用失败)")
                elif self._failures >= self.failure_threshold and self._state == self.CLOSED:
                    self._state = self.OPEN
                    logger.error(f"[熔断器] {self.name}: CLOSED→OPEN (连续{self._failures}次失败)")
            raise

class CircuitBreakerOpenError(Exception):
    pass

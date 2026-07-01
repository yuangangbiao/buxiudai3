# -*- coding: utf-8 -*-
import logging
import threading
from typing import Callable, Dict, List

logger = logging.getLogger(__name__)


class EventBus:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    obj._subscribers = {}
                    obj._sub_lock = threading.Lock()
                    cls._instance = obj
        return cls._instance

    @classmethod
    def get(cls):
        return cls()

    def subscribe(self, event_type: str, handler: Callable):
        with self._sub_lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)
            logger.info(f"Handler registered for event '{event_type}': {handler.__name__}")

    def unsubscribe(self, event_type: str, handler: Callable):
        with self._sub_lock:
            handlers = self._subscribers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)
                logger.info(f"Handler unregistered for event '{event_type}': {handler.__name__}")

    def publish(self, event_type: str, data: dict = None):
        handlers = []
        with self._sub_lock:
            handlers = list(self._subscribers.get(event_type, []))
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                logger.exception(f"Error in handler '{handler.__name__}' for event '{event_type}': {e}")

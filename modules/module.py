from abc import ABC, abstractmethod
import orjson
from queue import Queue
from events import BufferUpdated, GenerateUpdated, GenerateCleared


class Module(ABC):
    unmanaged_fields: list = ["gstate", "state", "queue"]

    id: str
    gstate: any
    queue: Queue

    def __init__(self, gstate, queue, from_data):
        self.gstate = gstate.copy()
        self.queue = queue

        for k, v in from_data.items():
            if k not in self.unmanaged_fields:
                setattr(self, k, v)

    def set_state(self, gstate):
        self.gstate = gstate.copy()

    def set_queue(self, queue):
        self.queue = queue

    def printb(self, message="", end="\n", flush=False):
        self.queue.put(BufferUpdated(message + end), block=False)

    def printg(self, message="", end="\n", flush=False):
        self.queue.put(GenerateUpdated(message + end), block=False)

    def clearg(self):
        self.queue.put(GenerateCleared(), block=False)

    @abstractmethod
    def on_activate(self):
        pass

    @abstractmethod
    def on_input(self, line):
        pass

    @abstractmethod
    def extra_json(self, d):
        pass

    def toJSON(self):
        d = {
            "id": self.id,
            "class": self.__class__.__name__,
        }
        for k, v in vars(self).items():
            if k not in self.unmanaged_fields:
                d[k] = v

        d = self.extra_json(d)

        return orjson.dumps(d, option=orjson.OPT_INDENT_2)

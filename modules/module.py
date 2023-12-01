from abc import ABC, abstractmethod
import json


class Module(ABC):
    unmanaged_fields: list = ["gstate", "state"]

    id: str
    gstate: any

    def __init__(self, from_data):
        self.gstate = None
        for k, v in from_data.items():
            if k not in self.unmanaged_fields:
                setattr(self, k, v)

    def set_state(self, gstate):
        self.gstate = gstate

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

        return json.dumps(d, indent=4)

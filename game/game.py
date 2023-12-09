import os
from language_model import Model
from modules import LocationGenerator, GameInit
import orjson
from pathlib import Path
from events import AddModule, ActivateModule, ConnectLocation
from dataclasses import dataclass
from textual.widgets import Static
from textual.app import App
from queue import Queue
import logging
from events import BufferUpdated, GenerateUpdated, GenerateCleared, SaveState
from pathlib import Path

# Style:
# title: bold deep_pink3
# prompt: deep_sky_blue4
# subsection: u
# list member: orange4
# unimportant: grey46


class GState:
    setting: str
    inventory: list
    health: list
    llm: Model
    history: list

    def __init__(self, queue, args):
        self.args = args
        self.setting = "Totally random"
        self.inventory = []
        self.history = []
        self.llm = Model(queue, args)

    def copy(self):
        n = GState(self.llm.queue, self.args)
        n.setting = self.setting
        n.inventory = self.inventory.copy()
        n.history = self.history.copy()
        return n


class Game:
    queue: Queue
    gstate: GState
    all_modules: dict
    current_module: str
    events: list

    def __init__(self, queue, args, from_save=None):
        self.queue = queue
        self.gstate = GState(queue, args)
        self.all_modules = {}
        self.current_module = None
        self.events = []

        if from_save:
            game_config = {}
            with open("save/game_loop.json", "r", encoding="utf-8") as f:
                game_config = orjson.loads(f.read())
                self.gstate.inventory = game_config.get("inventory")
                self.gstate.history = game_config.get("history")
                self.gstate.setting = game_config.get("setting")

            pathlist = Path(from_save).glob("modules/*.json")
            for path in pathlist:
                with open(path, "r", encoding="utf-8") as f:
                    c = orjson.loads(f.read())

                    modules = __import__("modules")
                    class_name = getattr(modules, c.get("class"))
                    instance = class_name(
                        gstate=self.gstate, queue=self.queue, from_data=c
                    )
                    self.events += [AddModule(instance)]

            self.events += [ActivateModule(game_config.get("current_module"))]
        else:
            self.gstate.history = []
            lg = GameInit.create(self.gstate, self.queue)
            self.events += [AddModule(lg), ActivateModule(lg.id)]

        self.flush_events()

    def printb(self, message="", end="\n", flush=False):
        self.queue.put(BufferUpdated(message + end), block=False)

    def printg(self, message="", end="\n", flush=False):
        self.queue.put(GenerateUpdated(message + end), block=False)

    def clearg(self):
        self.queue.put(GenerateCleared(), block=False)

    def execute(self, line):
        events = self.current_module.on_input(line)
        if events:
            self.events += events

        self.flush_events()
        self.save_state()

    def flush_events(self):
        while True:
            if len(self.events) == 0:
                break
            e = self.events.pop(0)

            if e.__class__.__name__ == "AddModule":
                self.all_modules[e.module.id] = e.module
            elif e.__class__.__name__ == "ActivateModule":
                self.current_module = self.all_modules[e.id]
                events = self.current_module.on_activate()
                if events:
                    self.events += events
            elif e.__class__.__name__ == "UpdateLocationDescription":
                self.all_modules[e.id].description = e.description
            elif e.__class__.__name__ == "SetSetting":
                self.gstate.setting = e.setting
                for m in self.all_modules.values():
                    m.set_state(self.gstate)
            elif e.__class__.__name__ == "UpdateInventory":
                self.gstate.inventory = e.new_inventory.copy()
                for m in self.all_modules.values():
                    m.set_state(self.gstate)
            elif e.__class__.__name__ == "AddHistory":
                event = e.event.strip()
                if event == "":
                    continue

                skip = False
                if e.skip_if_duplicate:
                    for h in self.gstate.history:
                        if event == h:
                            skip = True
                            break
                if skip:
                    continue

                self.gstate.history += [event]
                for m in self.all_modules.values():
                    m.set_state(self.gstate)
            elif e.__class__.__name__ == "DeleteModule":
                del self.all_modules[e.id]
                os.remove(f"save/modules/{e.id}.json")
            elif e.__class__.__name__ == "ConnectLocation":
                src = self.all_modules[e.src]
                dst = self.all_modules[e.dst]

                dst.exits["<<back>>"] = {
                    "name": src.name,
                    "id": src.id,
                }

                for k, ex in src.exits.items():
                    if ex.get("name") == dst.name:
                        src.exits[k]["id"] = dst.id

    def save_state(self):
        Path("save/modules").mkdir(parents=True, exist_ok=True)

        for id, module in self.all_modules.items():
            with open(f"save/modules/{id}.json", "wb") as f:
                f.write(module.toJSON())
        with open("save/game_loop.json", "wb") as f:
            f.write(
                orjson.dumps(
                    {
                        "current_module": self.current_module.id,
                        "setting": self.gstate.setting,
                        "inventory": self.gstate.inventory,
                        "history": self.gstate.history,
                    },
                    option=orjson.OPT_INDENT_2,
                )
            )

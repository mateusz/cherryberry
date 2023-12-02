import os
from language_model import Model
from modules import LocationGenerator
import json
from pathlib import Path
from events import AddModule, ActivateModule, ConnectLocation
from dataclasses import dataclass
from textual.widgets import Static
from textual.app import App
from queue import Queue
import logging

# Style:
# title: bold deep_pink3
# prompt: deep_sky_blue4
# subsection: u
# list member: orange4
# unimportant: grey46


class GState:
    setting: str
    inventory: object
    llm: Model

    def __init__(self, queue):
        # self.setting = "RPG game set in a modern world torn by war, with much fighting still going on. The player is a survivor in this dark and dangerous world."
        self.setting = """\
RPG game set in an expansive Canadian frozen wilderness in the \
aftermath of a geomagnetic disaster. There are no zombies -- only \
the cold and all the threats Mother Nature can muster.

The player is a lone survivor. Bright lights flare across the \
sky. The wind rages outside. A wolf howls in the distance. Supplies \
are scarce and the power mysteriously went out.  How much longer \
will the player survive?
        """
        self.inventory = {}
        self.llm = Model(queue)


class Game:
    queue: Queue
    gstate: GState
    all_modules: object
    current_module: str
    events: list

    def __init__(self, queue, from_save=None):
        self.queue = queue
        self.gstate = GState(queue)
        self.all_modules = {}
        self.current_module = None
        self.events = []

        if from_save:
            game_config = {}
            with open("save/game_loop.json", "r", encoding="utf-8") as f:
                game_config = json.loads(f.read())
                self.gstate.inventory = game_config.get("inventory")
                self.gstate.setting = game_config.get("setting")

            pathlist = Path(from_save).glob("modules/*.json")
            for path in pathlist:
                with open(path, "r", encoding="utf-8") as f:
                    c = json.loads(f.read())

                    modules = __import__("modules")
                    class_name = getattr(modules, c.get("class"))
                    instance = class_name(
                        gstate=self.gstate, queue=self.queue, from_data=c
                    )
                    self.events += [AddModule(instance)]

            self.events += [ActivateModule(game_config.get("current_module"))]
        else:
            lg = LocationGenerator.create_from_user_input(
                self.gstate, self.queue, "Adventure awaits!"
            )
            self.events += [AddModule(lg), ActivateModule(lg.id)]

        self.flush_events()

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
            elif e.__class__.__name__ == "UpdateInventory":
                self.gstate.inventory = e.new_inventory
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
        print("Saving state...")
        for id, module in self.all_modules.items():
            with open(f"save/modules/{id}.json", "w", encoding="utf-8") as f:
                f.write(module.toJSON())
        with open("save/game_loop.json", "w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "current_module": self.current_module.id,
                        "setting": self.gstate.setting,
                        "inventory": self.gstate.inventory,
                    },
                    sort_keys=True,
                    indent=4,
                )
            )

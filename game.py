import os
from language_model import Model
from modules import LocationGenerator
import json
from pathlib import Path
from events import AddModule, ActivateModule, ConnectLocation

class Game:

    def __init__(self, from_save=None):
        self.llm = Model()
        self.all_modules = {}
        self.current_module = None
        self.events = []
        if from_save:
            pathlist = Path(from_save).glob('modules/*.json')
            for path in pathlist:
                with open(path, "r", encoding="utf-8") as f:
                    c = json.loads(f.read())

                    modules = __import__('modules')
                    class_name = getattr(modules, c.get('class'))
                    instance = class_name(self.llm, from_data=c)
                    self.events += [AddModule(instance)]
            with open("save/game_loop.json", "r", encoding="utf-8") as f:
                c = json.loads(f.read())
                self.events += [ActivateModule(c.get("current_module"))]
        else:
            lg = LocationGenerator.create_from_user_input("Adventure awaits!", self.llm)
            self.events += [AddModule(lg), ActivateModule(lg.id)]

    def run(self):
        while True:

            while True:
                if len(self.events)==0:
                    break
                e = self.events.pop(0)

                if e.__class__.__name__=='AddModule':
                    self.all_modules[e.module.id] = e.module
                elif e.__class__.__name__=='ActivateModule':
                    self.current_module = self.all_modules[e.id]
                    events = self.current_module.on_activate()
                    if events:
                        self.events += events
                elif e.__class__.__name__=='DeleteModule':
                    del self.all_modules[e.id]
                    os.remove(f"save/modules/{e.id}.json")
                elif e.__class__.__name__=='ConnectLocation':
                    src = self.all_modules[e.src]
                    dst = self.all_modules[e.dst]

                    dst.exits["<<back>>"] = {
                        "name": src.name,
                        "id": src.id,
                    }

                    for k, ex in src.exits.items():
                        if ex.get('name')==dst.name:
                           src.exits[k]['id'] = dst.id

            for id,module in self.all_modules.items():
                with open(f"save/modules/{id}.json", "w", encoding="utf-8") as f:
                    f.write(module.toJSON())
            with open("save/game_loop.json", "w", encoding="utf-8") as f:
                f.write(json.dumps({
                    "current_module": self.current_module.id
                }, sort_keys=True, indent=4))

            line = input("> ")
            events = self.current_module.on_input(line)
            if events:
                self.events += events

        

if __name__ == "__main__":
    if os.path.exists('save/game_loop.json'):
        g = Game(from_save="save")
        g.run()
    else:
        g = Game()
        g.run()
        # "a high-fantasy game, forest location, a lot of nature."
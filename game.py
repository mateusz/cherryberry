import os
from language_model import Model
from modules import Initialization
import json
from pathlib import Path


def game_loop(starter_data=None, from_save=None):
    llm = Model()
    all_modules = {}
    if from_save:
        pathlist = Path(from_save).glob('modules/*.json')
        for path in pathlist:
            with open(path, "r", encoding="utf-8") as f:
                c = json.loads(f.read())

                modules = __import__('modules')
                class_name = getattr(modules, c.get('class'))
                instance = class_name(llm, from_data=c)
                all_modules[c.get('id')] = instance
        with open("save/game_loop.json", "r", encoding="utf-8") as f:
            c = json.loads(f.read())
            current_module = all_modules.get(c.get("current_module"))
    else:
        all_modules = {
            "Initialization": Initialization(llm, starter_data),
        }
        current_module = all_modules["Initialization"]

    current_module.on_activate()
    while True:
        for id,module in all_modules.items():
            with open(f"save/modules/{id}.json", "w", encoding="utf-8") as f:
                f.write(module.toJSON())

        with open("save/game_loop.json", "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "current_module": current_module.id
            }, sort_keys=True, indent=4))

        line = input("> ")
        events = current_module.on_input(line)
        if not events:
            continue
        for e in events:
            if e.__class__.__name__=='AddModule':
                all_modules[e.module.id] = e.module
            elif e.__class__.__name__=='ActivateModule':
                current_module = all_modules[e.id]
                current_module.on_activate()

        

if __name__ == "__main__":
    if os.path.exists('save/game_loop.json'):
        game_loop(starter_data="a high-fantasy game, forest location, a lot of nature.", from_save="save")
    else:
        game_loop(starter_data="a high-fantasy game, forest location, a lot of nature.")
from enum import Enum
import json
import hashlib
from events import AddModule, ActivateModule, DeleteModule
import shlex
import re
    
class Location_States(Enum):
    START = 1

class Location():
    @staticmethod
    def create_from_requirements(name, llm, requirements):
        print(f"[Generating location description from '{requirements}'...]")
        description = llm.generate_location(requirements)
        print("[Looking for exits...]")
        try:
            exits = llm.find_exits(description)
        except Exception as exc:
            print("[No exits found, but you can use the ENTER command]")
            exits = {}

        return Location(llm, {
            "name": name,
            "state": Location_States.START,
            "description": description,
            "exits": exits,
        })

    @staticmethod
    def create_from_exit(llm, previous, exit):
        print("[Generating location description from exit]")
        description = llm.generate_location_from_exit(previous, exit.get('name'), exit.get('description'))
        print("[Looking for exits...]")
        try:
            exits = llm.find_exits(description)
        except Exception as exc:
            print("[No exits found, but you can use the ENTER command]")
            exits = {}

        return Location(llm, {
            "name": exit.get('name'),
            "state": Location_States.START,
            "description": description,
            "exits": exits,
        })
        
    def on_activate(self):
        self.describe()

    def __init__(self, llm, from_data):
        self.llm=llm
        self.name = from_data["name"]
        self.state = Location_States(from_data["state"])
        self.description = from_data["description"]
        self.exits = from_data["exits"]
        self.id = hashlib.md5(self.description.encode('utf-8')).hexdigest()

    def on_input(self, line):
        cmd = shlex.split(line)

        if cmd[0]=='look' or cmd[0]=='l':
            self.describe()
        elif cmd[0]=='go' or cmd[0]=='g':
            exit_number = int(cmd[1]) - 1
            key = list(self.exits.keys())[exit_number]
            ex = list(self.exits.values())[exit_number]
            print(f"Taking the exit '{ex.get('name')}'")

            if ex.get('id', None):
                return [
                    ActivateModule(ex.get('id')),
                ]
            else:
                l = Location.create_from_exit(self.llm, self.description, ex)
                l.exits["<<back>>"] = {
                    "name": self.name,
                    "id": self.id,
                }
                self.exits[key]["id"] = l.id

                return [
                    AddModule(l),
                    ActivateModule(l.id),
                ]
        elif cmd[0]=='gn' or cmd[0]=='gon' or cmd[0]=='gonew':
            ex = {
                "name": cmd[1],
                "description": cmd[2]
            }

            i = 1
            for k in self.exits.keys():
                if k.startswith("<<custom"):
                    n = int(re.sub(r'<<custom([0-9]*)>>', '\\1', k))
                    if n>=i:
                        i = n+1

            self.exits[f"<<custom{i}>>"] = ex
            print(f"Entering '{cmd[1]}'")
            l = Location.create_from_exit(self.llm, self.description, ex)
            l.exits["<<back>>"] = {
                "name": self.name,
                "id": self.id,
            }
            self.exits[f"<<custom{i}>>"]["id"] = l.id

            return [
                AddModule(l),
                ActivateModule(l.id),
            ]
        elif cmd[0]=='gd' or cmd[0]=='god' or cmd[0]=='godel':
            exit_number = int(cmd[1]) - 1
            key = list(self.exits.keys())[exit_number]
            ex = list(self.exits.values())[exit_number]

            if key=="<<back>>":
                print("Cannot delete the return path, the world will collapse into singularity.")
            else:
                print(f"Deleting the exit '{ex.get('name')}'. It disappears in a wisp of smoke...")
                del self.exits[key]
                if ex.get('id', None):
                    return [
                        DeleteModule(ex.get('id')),
                    ]
        else:
            print("Command not recognised")
    

    def describe(self):
        print()
        print(f"### {self.name} ###")
        print()
        print(f"{self.description} [Ref: {self.id}]")
        print()
        print("Exits (use 'go NUM' to take an exit):")
        i = 0
        for key,ex in self.exits.items():
            i += 1
            if key=='<<back>>':
                print(f"[{i}] {ex.get('name')} (backtrack)")
            elif ex.get('id', None):
                print(f"[{i}] {ex.get('name')} -> {ex.get('description')} (already visited)")
            else:
                print(f"[{i}] {ex.get('name')} -> {ex.get('description')}")
        
    def toJSON(self):
        return json.dumps({
            "id": self.id,
            "name": self.name,
            "class": self.__class__.__name__,
            "state": self.state.value,
            "description": self.description,
            "exits": self.exits
        }, sort_keys=True, indent=4)
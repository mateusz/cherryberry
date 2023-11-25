from enum import Enum
import json
import hashlib
from events import AddModule, ActivateModule

    
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
            print(exc)
            print("[Failed. Redo the action to try again]")

        return Location(llm, {
            "name": name,
            "state": Location_States.START,
            "description": description,
            "exits": exits,
        })

    @staticmethod
    def create_from_exit(name, llm, previous, exit):
        print("[Generating location description from exit]")
        description = llm.generate_location_from_exit(previous, exit.get('name'), exit.get('description'))
        print("[Looking for exits...]")
        try:
            exits = llm.find_exits(description)
        except Exception as exc:
            print(exc)
            print("[Failed. Redo the action to try again]")

        return Location(llm, {
            "name": name,
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
        if line=='look' or line=='l':
            self.describe()
        if line.startswith('go'):
            exit_number = int(line.split(" ")[1]) - 1
            key = list(self.exits.keys())[exit_number]
            ex = list(self.exits.values())[exit_number]
            print(f"Taking the exit '{ex.get('name')}'")

            if ex.get('id', None):
                return [
                    ActivateModule(ex.get('id')),
                ]
            else:
                try:
                    l = Location.create_from_exit(ex.get('name'), self.llm, self.description, ex)
                    l.exits["<<back>>"] = {
                        "name": self.name,
                        "id": self.id,
                    }
                    self.exits[key]["id"] = l.id

                    return [
                        AddModule(l),
                        ActivateModule(l.id),
                    ]
                except Exception as exc:
                    print(exc)
                    print("Failed. Repeat the action to try again")

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
from enum import Enum
import json
import hashlib
from events import AddModule, ActivateModule, DeleteModule, ConnectLocation
from .action import Action
import shlex
import re
    
class Location_States(Enum):
    START = 1

class Location():
    @staticmethod
    def create(name, description, exits):
        return Location({
            "name": name.strip(),
            "description": description.strip(),
            "exits": exits,
            "state": Location_States.START,
            "id": hashlib.md5(description.encode('utf-8')).hexdigest()
        })
        
    def on_activate(self):
        self.describe()

    def __init__(self, from_data):
        self.gstate=None
        self.name = from_data["name"]
        self.state = Location_States(from_data["state"])
        self.description = from_data["description"]
        self.exits = from_data["exits"]
        self.id = from_data["id"]

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
                l = LocationGenerator.create_from_exit(self, ex)
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
            l = LocationGenerator.create_from_exit(self, ex)

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
        elif cmd[0]=='act' or cmd[0]=='a':
            l = Action.create(self, cmd[1])
            return [
                AddModule(l),
                ActivateModule(l.id),
            ]
        elif cmd[0]=='i' or cmd[0]=='inv' or cmd[0]=='inventory':
            if len(self.gstate.inventory)==0:
                print("Your inventory is empty")
            else:
                print("Your inventory:")
                for k,v in self.gstate.inventory.items():
                    print(f"[{k}] -> {v}")
        else:
            print("Command not recognised")
    

    def describe(self):
        print()
        print(f"### {self.name} ###")
        print()
        print(f"{self.description} [Ref: {self.id}]")
        print()
        self.describe_exits()
        
    def describe_exits(self):
        print("Exits (use 'go NUM' to take an exit):")
        i = 0
        for key,ex in self.exits.items():
            i += 1
            if key=='<<back>>':
                print(f"[{i}] {ex.get('name')} (backtrack)")
            elif ex.get('id', None):
                print(f"[{i}] {ex.get('name')} (visited) -> {ex.get('description')} (already visited)")
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
        }, indent=4)
    
class LocationGenerator_States(Enum):
    GET_REQUIREMENTS = 1
    AFTER_REQUIREMENTS = 2
    AFTER_DESCRIPTION = 3

class LocationGenerator():
    @staticmethod
    def create_from_user_input(name):
        return LocationGenerator({
            "name": name,
            "requirements": "",
            "from_previous_id": None,
            "from_previous_name": None,
            "from_previous_description": None,
            "from_exit": None,
            "state": LocationGenerator_States.GET_REQUIREMENTS,
            "description": "",
            "exits": {},
            "id": "LocationGenerator",
        })

    @staticmethod
    def create_from_exit(previous, exit):
        return LocationGenerator({
            "name": exit.get('name'),
            "requirements": None,
            "from_previous_name": previous.name,
            "from_previous_description": previous.description,
            "from_previous_id": previous.id,
            "from_exit": exit,
            "state": LocationGenerator_States.AFTER_REQUIREMENTS,
            "description": "",
            "exits": {},
            "id": "LocationGenerator",
        })


    def __init__(self, from_data):
        self.gstate = None
        self.name = from_data["name"]
        self.requirements = from_data["requirements"]
        self.from_exit = from_data["from_exit"]
        self.from_previous_id = from_data["from_previous_id"]
        self.from_previous_name = from_data["from_previous_name"]
        self.from_previous_description = from_data["from_previous_description"]
        self.state = LocationGenerator_States(from_data["state"])
        self.description = from_data["description"]
        self.exits = from_data["exits"]
        self.id = from_data["id"]
        if self.state==LocationGenerator_States.AFTER_DESCRIPTION:
            self.location = Location.create(self.name, self.description, self.exits)
        else:
            self.location = None

    def on_activate(self):
        if self.state==LocationGenerator_States.GET_REQUIREMENTS:
            print("Provide short description of the location, or ENTER for default:")
        elif self.state==LocationGenerator_States.AFTER_REQUIREMENTS:
            self.generate_description_from_requirements()
        elif self.state==LocationGenerator_States.AFTER_DESCRIPTION:
            self.location.describe()
            print()
            print("Do you want to keep this location? [KEEP/(reg)enerate/(rew)rite]")

    def on_input(self, line):
        if self.state==LocationGenerator_States.GET_REQUIREMENTS:
            if line=="":
                self.requirements = "abandoned house"
            else:
                self.requirements=line
            self.generate_description_from_requirements()
        elif self.state==LocationGenerator_States.AFTER_DESCRIPTION:
            if line=="reg" or line=="regenerate":
                self.description = ""
                self.exits = {}
                self.state = LocationGenerator_States.AFTER_REQUIREMENTS
                self.generate_description_from_requirements()
            elif line=="rew" or line=="rewrite":
                self.requirements = ""
                self.description = ""
                self.exits = {}
                self.state = LocationGenerator_States.GET_REQUIREMENTS
                print()
                print("Provide short description of the location, or ENTER for default:")
            elif line=="" or line=="keep":
                events = [
                    DeleteModule(self.id),
                    AddModule(self.location),
                ]

                if self.from_previous_id:
                    events += [ConnectLocation(self.from_previous_id, self.location.id)]

                events += ActivateModule(self.location.id),

                return events

    def generate_description_from_requirements(self):
        print(f"### {self.name} ###")
        if self.requirements:
            stream=self.gstate.llm.generate_location(self.gstate.setting, self.requirements)
        else:
            stream=self.gstate.llm.generate_location_from_exit(
                self.gstate.setting,
                self.from_previous_description,
                self.from_exit.get('name'),
                self.from_exit.get('description')
            )

        out=""
        for output in stream:
            out += output['choices'][0]['text']
            print(output['choices'][0]['text'], end='', flush=True)
        print()

        self.description = out.strip()
            
        print("[Looking for exits...]")
        try:
            self.exits = self.gstate.llm.find_exits(self.description)
        except Exception:
            print("[No exits found]")
            self.exits = {}

        self.location = Location.create(self.name, self.description, self.exits)
        self.state = LocationGenerator_States.AFTER_DESCRIPTION
        self.location.describe_exits()

        print()
        print("Do you want to keep this location? [KEEP/(reg)enerate/(rew)rite]")

    def toJSON(self):
        return json.dumps({
            "id": self.id,
            "name": self.name,
            "class": self.__class__.__name__,
            "requirements": self.requirements,
            "from_previous_id": self.from_previous_id,
            "from_previous_name": self.from_previous_name,
            "from_previous_description": self.from_previous_description,
            "from_exit": self.from_exit,
            "state": self.state.value,
            "description": self.description,
            "exits": self.exits
        }, indent=4)
from enum import Enum
import json
import hashlib
from events import AddModule, ActivateModule, DeleteModule, ConnectLocation, UpdateLocationDescription, UpdateInventory
import shlex
import re
    
class Action_States(Enum):
    BEFORE_PERMISSIBLE = 1
    BEFORE_CONSEQUENCES = 2
    BEFORE_UPDATE_DESCRIPTION = 3
    BEFORE_UPDATE_INVENTORY = 4
    END = 5

class Action():
    @staticmethod
    def create(location, action):
        return Action({
            "location_description": location.description.strip(),
            "location_id": location.id,
            "action": action,
            "permissible": "",
            "consequences": "",
            "new_description": "",
            "new_inventory": "",
            "skip_description": False,
            "state": Action_States.BEFORE_PERMISSIBLE,
        })
    
    def __init__(self, from_data):
        self.gstate = None
        self.location_description = from_data["location_description"]
        self.location_id = from_data["location_id"]
        self.action = from_data["action"]
        self.permissible = from_data["permissible"]
        self.consequences = from_data["consequences"]
        self.new_description = from_data["new_description"]
        self.new_inventory = from_data["new_inventory"]
        self.skip_description = from_data["skip_description"]
        self.name = "Action"
        self.id = "Action"
        self.state = Action_States(from_data["state"])
        print("Does the updated inventory make sense? [KEEP/(reg)enerate/(s)kip/(d)elete N]")

    def toJSON(self):
        return json.dumps({
            "id": self.id,
            "name": self.name,
            "class": self.__class__.__name__,
            "state": self.state.value,
            "location_description": self.location_description,
            "location_id": self.location_id,
            "action": self.action,
            "permissible": self.permissible,
            "consequences": self.consequences,
            "new_description": self.new_description,
            "new_inventory": self.new_inventory,
            "skip_description": self.skip_description
        }, indent=4)

    def on_activate(self):
        if self.state==Action_States.BEFORE_PERMISSIBLE:
            print(f"* Action: {self.action}")
            self.action_permissible()
        elif self.state==Action_States.BEFORE_CONSEQUENCES:
            print(f"* Action: {self.action}")
            print(f"* Permissibility: {self.permissible}")
            print("Does this statement make sense? [KEEP/(reg)enerate]")
        elif self.state==Action_States.BEFORE_UPDATE_DESCRIPTION:
            print(f"* Action: {self.action}")
            print(f"* Permissibility: {self.permissible}")
            print(f"* Consequences: {self.consequences}")
            print("Do the consequences make sense? [KEEP/(reg)enerate]")
        elif self.state==Action_States.BEFORE_UPDATE_INVENTORY:
            print(f"* Action: {self.action}")
            print(f"* Permissibility: {self.permissible}")
            print(f"* Consequences: {self.consequences}")
            print(f"* New description: {self.new_description}")
            print("Would you like to keep the new description? [KEEP/(reg)enerate/(s)kip]")
        elif self.state==Action_States.END:
            print(f"* Action: {self.action}")
            print(f"* Permissibility: {self.permissible}")
            print(f"* Consequences: {self.consequences}")
            if self.skip_description:
                print("* New description: [skipped]")
            else:
                print(f"* New description: {self.new_description}")
            self.print_inventory()
            print("Does the updated inventory make sense? [KEEP/(reg)enerate/(s)kip/(d)elete N/(a)dd 'item' 'description']")

    def on_input(self, line):
        if self.state==Action_States.BEFORE_CONSEQUENCES:
            if line=="reg" or line=="regenerate":
                self.state=Action_States.BEFORE_PERMISSIBLE
                self.action_permissible()
            else:
                self.generate_consequences()
        elif self.state==Action_States.BEFORE_UPDATE_DESCRIPTION:
            if line=="reg" or line=="regenerate":
                self.state=Action_States.BEFORE_CONSEQUENCES
                self.generate_consequences()
            else:
                self.update_description()
        elif self.state==Action_States.BEFORE_UPDATE_INVENTORY:
            if line=="reg" or line=="regenerate":
                self.state=Action_States.BEFORE_UPDATE_DESCRIPTION
                self.update_description()
            elif line=="s" or line=="skip":
                self.skip_description = True
                self.update_inventory()
            else:
                self.update_inventory()
        elif self.state==Action_States.END:
            cmd = shlex.split(line)

            if len(cmd)==0:
                self.gstate.inventory = self.new_inventory
                events = [
                    DeleteModule(self.id),
                ]

                if not self.skip_description:
                    events += [UpdateLocationDescription(self.location_id, self.new_description)]

                events += [
                    UpdateInventory(self.new_inventory),
                    ActivateModule(self.location_id),
                ]
                return events

            elif cmd[0]=="reg" or cmd[0]=="regenerate":
                self.state=Action_States.BEFORE_UPDATE_INVENTORY
                self.update_inventory()

            elif cmd[0]=="d" or cmd[0]=="delete":
                item_number = int(cmd[1]) - 1
                key = list(self.new_inventory.keys())[item_number]
                print(f"Deleting item '{key}'. It disappears in a wisp of smoke...")
                del self.new_inventory[key]
                self.print_inventory()
                print("Does the updated inventory make sense? [KEEP/(reg)enerate/(s)kip/(d)elete N/(a)dd 'item' 'description']")

            elif cmd[0]=="a" or cmd[0]=="add":
                self.new_inventory[cmd[1]] = cmd[2]
                print(f"Added item '{cmd[1]}'")
                self.print_inventory()
                print("Does the updated inventory make sense? [KEEP/(reg)enerate/(s)kip/(d)elete N/(a)dd 'item' 'description']")

            elif cmd[0]=="s" or cmd[0]=="skip":
                events = [
                    DeleteModule(self.id),
                ]

                if not self.skip_description:
                    events += [UpdateLocationDescription(self.location_id, self.new_description)]
                
                events += [
                    ActivateModule(self.location_id),
                ]
                return events

            else:
                print("Command not recognised")

    def action_permissible(self):
        print("[Deciding if the action is permissible]")
        stream = self.gstate.llm.action_permissible(
            self.location_description, self.gstate.inventory, self.action
        )

        out=""
        for output in stream:
            out += output['choices'][0]['text']
            print(output['choices'][0]['text'], end='', flush=True)
        print()

        self.permissible = out.strip()
        self.state = Action_States.BEFORE_CONSEQUENCES

        print("Does this statement make sense? [KEEP/(reg)enerate]")

    def generate_consequences(self):
        print("[Generating consequences]")
        stream = self.gstate.llm.consequences(
            self.location_description, self.gstate.inventory, self.action, self.permissible
        )

        out=""
        for output in stream:
            out += output['choices'][0]['text']
            print(output['choices'][0]['text'], end='', flush=True)
        print()

        self.consequences = out.strip()
        self.state = Action_States.BEFORE_UPDATE_DESCRIPTION

        print("Do the consequences make sense? [KEEP/(reg)enerate]")

    def update_description(self):
        print("[Generating updated description]")
        stream = self.gstate.llm.update_description(
            self.location_description, self.action, self.consequences
        )

        out=""
        for output in stream:
            out += output['choices'][0]['text']
            print(output['choices'][0]['text'], end='', flush=True)
        print()

        self.new_description = out.strip()
        self.state = Action_States.BEFORE_UPDATE_INVENTORY

        print("Would you like to keep the new description? [KEEP/(reg)enerate/(s)kip]")

    def update_inventory(self):
        print("[Generating updated inventory]")
        try:
            self.new_inventory = self.gstate.llm.update_inventory(
                self.gstate.inventory, self.location_description, self.action, self.consequences
            )
        except Exception:
            print("[No changes found]")
            self.new_inventory = self.gstate.inventory

        self.state = Action_States.END

        self.print_inventory()
        print("Does the updated inventory make sense? [KEEP/(reg)enerate/(s)kip/(d)elete N/(a)dd 'item' 'description']")

    def print_inventory(self):
        if len(self.new_inventory)==0:
            print("* New inventory is empty")
        else:
            print("* New inventory:")
            i = 0
            for k,v in self.new_inventory.items():
                i+=1
                print(f"[{i}] -> {k} ({v})")
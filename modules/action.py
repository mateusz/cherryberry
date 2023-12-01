from enum import Enum
from .module import Module
from events import (
    ActivateModule,
    DeleteModule,
    UpdateLocationDescription,
    UpdateInventory,
)
import shlex


class Action_States(Enum):
    BEGIN = 1
    AFTER_PERMISSIBLE = 2
    AFTER_CONSEQUENCES = 3
    AFTER_UPDATED_DESCRIPTION = 4
    AFTER_UPDATED_INVENTORY = 5
    END = 6


class Action(Module):
    unmanaged_fields = ["gstate", "state"]

    location_description: str
    location_id: str
    action: str
    permissible: str
    consequences: str
    new_description: str
    new_inventory: str
    skip_description: bool
    skip_inventory: bool
    state: Action_States

    @staticmethod
    def create(location, action):
        return Action(
            {
                "name": "Action",
                "id": "Action",
                "location_description": location.description.strip(),
                "location_id": location.id,
                "action": action,
                "permissible": "",
                "consequences": "",
                "new_description": "",
                "new_inventory": "",
                "skip_description": False,
                "skip_inventory": False,
                "state": Action_States.BEGIN,
            }
        )

    def __init__(self, from_data):
        super().__init__(from_data)
        self.state = Action_States(from_data["state"])
        print(
            "Does the updated inventory make sense? [KEEP/(reg)enerate/(s)kip/(d)elete N]"
        )

    def on_activate(self):
        if self.state == Action_States.BEGIN:
            print(f"* Action: {self.action}")
            self.action_permissible()
        elif self.state == Action_States.AFTER_PERMISSIBLE:
            print(f"* Action: {self.action}")
            print(f"* Permissibility: {self.permissible}")
            print("Does this statement make sense? [KEEP/(reg)enerate]")
        elif self.state == Action_States.AFTER_CONSEQUENCES:
            print(f"* Action: {self.action}")
            print(f"* Permissibility: {self.permissible}")
            print(f"* Consequences: {self.consequences}")
            print(
                "Do the consequences make sense? [KEEP/(reg)enerate/keep and skip to (i)nventory/keep and skip to (e)nd]"
            )
        elif self.state == Action_States.AFTER_UPDATED_DESCRIPTION:
            print(f"* Action: {self.action}")
            print(f"* Permissibility: {self.permissible}")
            print(f"* Consequences: {self.consequences}")
            print(f"* New description: {self.new_description}")
            print(
                "Would you like to keep the new description? [KEEP/(reg)enerate/(s)kip/keep and skip to (e)nd]"
            )
        elif self.state == Action_States.AFTER_UPDATED_INVENTORY:
            print(f"* Action: {self.action}")
            print(f"* Permissibility: {self.permissible}")
            print(f"* Consequences: {self.consequences}")
            if self.skip_description:
                print("* New description: [skipped]")
            else:
                print(f"* New description: {self.new_description}")
            self.print_inventory()
            print(
                "Does the updated inventory make sense? [KEEP/(reg)enerate/(s)kip/(d)elete N/(a)dd 'item' 'description']"
            )

    def on_input(self, line):
        if self.state == Action_States.AFTER_PERMISSIBLE:
            if line == "reg" or line == "regenerate":
                self.state = Action_States.BEGIN
                self.action_permissible()
            else:
                self.generate_consequences()

        elif self.state == Action_States.AFTER_CONSEQUENCES:
            if line == "reg" or line == "regenerate":
                self.state = Action_States.AFTER_PERMISSIBLE
                self.generate_consequences()
            elif line == "i" or line == "inv" or line == "inventory":
                self.state = Action_States.AFTER_UPDATED_DESCRIPTION
                self.skip_description = True
                self.update_inventory()
            elif line == "e" or line == "end":
                self.skip_description = True
                self.state = Action_States.AFTER_UPDATED_INVENTORY
                return self.finalize()
            else:
                self.update_description()

        elif self.state == Action_States.AFTER_UPDATED_DESCRIPTION:
            if line == "reg" or line == "regenerate":
                self.state = Action_States.AFTER_CONSEQUENCES
                self.update_description()
            elif line == "s" or line == "skip":
                self.state = Action_States.AFTER_UPDATED_INVENTORY
                self.skip_description = True
                self.update_inventory()
            elif line == "e" or line == "end":
                self.state = Action_States.END
                self.skip_inventory = True
                return self.finalize()
            else:
                self.update_inventory()

        elif self.state == Action_States.AFTER_UPDATED_INVENTORY:
            cmd = shlex.split(line)

            if len(cmd) == 0:
                self.state = Action_States.END
                return self.finalize()

            elif cmd[0] == "reg" or cmd[0] == "regenerate":
                self.state = Action_States.AFTER_UPDATED_DESCRIPTION
                self.update_inventory()

            elif cmd[0] == "d" or cmd[0] == "delete":
                item_number = int(cmd[1]) - 1
                key = list(self.new_inventory.keys())[item_number]
                print(f"Deleting item '{key}'. It disappears in a wisp of smoke...")
                del self.new_inventory[key]
                self.print_inventory()
                print(
                    "Does the updated inventory make sense? [KEEP/(reg)enerate/(s)kip/(d)elete N/(a)dd 'item' 'description']"
                )

            elif cmd[0] == "a" or cmd[0] == "add":
                self.new_inventory[cmd[1]] = cmd[2]
                print(f"Added item '{cmd[1]}'")
                self.print_inventory()
                print(
                    "Does the updated inventory make sense? [KEEP/(reg)enerate/(s)kip/(d)elete N/(a)dd 'item' 'description']"
                )

            elif cmd[0] == "s" or cmd[0] == "skip":
                self.state = Action_States.END
                self.skip_inventory = True
                return self.finalize()

            else:
                print("Command not recognised")

    def action_permissible(self):
        print("[Deciding if the action is permissible]")
        stream = self.gstate.llm.action_permissible(
            self.location_description, self.gstate.inventory, self.action
        )

        out = ""
        for output in stream:
            out += output["choices"][0]["text"]
            print(output["choices"][0]["text"], end="", flush=True)
        print()

        self.permissible = out.strip()
        self.state = Action_States.AFTER_PERMISSIBLE

        print("Does this statement make sense? [KEEP/(reg)enerate]")

    def generate_consequences(self):
        print("[Generating consequences]")
        stream = self.gstate.llm.consequences(
            self.location_description,
            self.gstate.inventory,
            self.action,
            self.permissible,
        )

        out = ""
        for output in stream:
            out += output["choices"][0]["text"]
            print(output["choices"][0]["text"], end="", flush=True)
        print()

        self.consequences = out.strip()
        self.state = Action_States.AFTER_CONSEQUENCES

        print(
            "Do the consequences make sense? [KEEP/(reg)enerate/keep and skip to (i)nventory/keep and skip to (e)nd]"
        )

    def update_description(self):
        print("[Generating updated description]")
        stream = self.gstate.llm.add_description(
            self.location_description, self.action, self.consequences
        )

        print(self.location_description)
        out = ""
        for output in stream:
            out += output["choices"][0]["text"]
            print(output["choices"][0]["text"], end="", flush=True)
        print()

        self.new_description = self.location_description + "\n\n" + out.strip()
        self.state = Action_States.AFTER_UPDATED_DESCRIPTION

        print(
            "Would you like to keep the new description? [KEEP/(reg)enerate/(s)kip/keep and skip to (e)nd]"
        )

    def update_inventory(self):
        self.new_inventory = self.gstate.inventory
        try:
            print("[Looking for items to remove]")
            remove_inventory = self.gstate.llm.remove_inventory(
                self.gstate.inventory,
                self.location_description,
                self.action,
                self.consequences,
            )
            for k, v in remove_inventory.items():
                if k in self.new_inventory:
                    del self.new_inventory[k]

            print("[Looking for items to add]")
            add_inventory = self.gstate.llm.add_inventory(
                self.gstate.inventory,
                self.location_description,
                self.action,
                self.consequences,
            )
            for k, v in add_inventory.items():
                self.new_inventory[k] = v

        except Exception as e:
            print("[No changes found]")
            self.new_inventory = self.gstate.inventory

        self.state = Action_States.AFTER_UPDATED_INVENTORY

        self.print_inventory()
        print(
            "Does the updated inventory make sense? [KEEP/(reg)enerate/(s)kip/(d)elete N/(a)dd 'item' 'description']"
        )

    def print_inventory(self):
        if self.skip_inventory:
            print("* New inventory: [skipped]")
        elif len(self.new_inventory) == 0:
            print("* New inventory is empty")
        else:
            print("* New inventory:")
            i = 0
            for k, v in self.new_inventory.items():
                i += 1
                print(f"[{i}] -> {k} ({v})")

    def finalize(self):
        if not self.skip_inventory:
            self.gstate.inventory = self.new_inventory

        events = [
            DeleteModule(self.id),
        ]

        if not self.skip_description:
            events += [
                UpdateLocationDescription(self.location_id, self.new_description)
            ]

        if not self.skip_inventory:
            events += [
                UpdateInventory(self.new_inventory),
            ]

        events += [
            ActivateModule(self.location_id),
        ]
        return events

    def extra_json(self, d):
        d["state"] = self.state.value
        return d

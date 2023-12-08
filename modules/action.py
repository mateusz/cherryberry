from enum import Enum
from .module import Module
from events import (
    ActivateModule,
    DeleteModule,
    UpdateLocationDescription,
    UpdateInventory,
    AddHistory,
)
import shlex
import re


class Action_States(Enum):
    BEGIN = 1
    AFTER_PERMISSIBLE = 2
    AFTER_CONSEQUENCES = 3
    AFTER_UPDATED_DESCRIPTION = 4
    AFTER_UPDATED_INVENTORY = 5
    END = 6


class Action(Module):
    unmanaged_fields = ["gstate", "state", "queue"]

    location_description: str
    location_id: str
    action: str
    action_items: list
    consequences: str
    new_description: str
    new_inventory: list
    skip_description: bool
    skip_inventory: bool
    state: Action_States

    @staticmethod
    def create(gstate, queue, location, action):
        a = Action(
            gstate,
            queue,
            {
                "name": "Action",
                "id": "Action",
                "location_description": location.description.strip(),
                "location_id": location.id,
                "action": action,
                "action_items": [],
                "consequences": "",
                "new_description": "",
                "new_inventory": "",
                "skip_description": False,
                "skip_inventory": False,
                "state": Action_States.BEGIN,
            },
        )
        return a

    def __init__(self, gstate, queue, from_data):
        super().__init__(gstate, queue, from_data)
        self.state = Action_States(from_data["state"])

    def on_activate(self):
        if self.state == Action_States.BEGIN:
            self.printb()
            self.printb(f"[orange4]Action[/]: {self.action}")
            self.printb()
            self.get_action_items()
            self.generate_consequences()
        elif self.state == Action_States.AFTER_CONSEQUENCES:
            self.printb()
            self.printb(f"[orange4]Action[/]: {self.action}")
            self.print_action_items()
            self.printb(f"[orange4]Consequences[/]: {self.consequences}")
            self.printb()
            self.printb(
                "[deep_sky_blue4]Do the consequences make sense? [KEEP/(reg)enerate/keep and skip to (i)nventory/keep and skip to (e)nd][/]"
            )
        elif self.state == Action_States.AFTER_UPDATED_DESCRIPTION:
            self.printb()
            self.printb(f"[orange4]Action[/]: {self.action}")
            self.print_action_items()
            self.printb(f"[orange4]Consequences[/]: {self.consequences}")
            if self.skip_description:
                self.printb("[orange4]New description[/]: [i]skipped[/i]")
            else:
                self.printb(f"[orange4]New description[/]: {self.new_description}")
            self.printb()
            self.printb(
                "[deep_sky_blue4]Would you like to keep the new description? [KEEP/(reg)enerate/(s)kip/keep and skip to (e)nd][/]"
            )
        elif self.state == Action_States.AFTER_UPDATED_INVENTORY:
            self.printb()
            self.printb(f"[orange4]Action[/]: {self.action}")
            self.print_action_items()
            self.printb(f"[orange4]Consequences[/]: {self.consequences}")
            if self.skip_description:
                self.printb("[orange4]New description[/]: [i]skipped[/i]")
            else:
                self.printb(f"[orange4]New description[/]: {self.new_description}")
            self.print_inventory()
            self.printb()
            self.printb(
                "[deep_sky_blue4]Does the updated inventory make sense? [KEEP/(reg)enerate/(s)kip/(d)elete N/(a)dd 'item' 'description'][/]"
            )

    def on_input(self, line):
        if self.state == Action_States.AFTER_CONSEQUENCES:
            if line == "reg" or line == "regenerate":
                self.state = Action_States.BEGIN
                self.get_action_items()
                self.generate_consequences()

            elif line == "i" or line == "inv" or line == "inventory":
                self.state = Action_States.AFTER_UPDATED_DESCRIPTION
                self.skip_description = True
                self.update_inventory()
            elif line == "e" or line == "end":
                self.skip_description = True
                self.skip_inventory = True
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
                key = self.new_inventory[item_number]
                self.printb(
                    f"Deleting item '{key}'. It disappears in a wisp of smoke..."
                )
                del self.new_inventory[item_number]
                self.print_inventory()
                self.printb(
                    "[deep_sky_blue4]Does the updated inventory make sense? [KEEP/(reg)enerate/(s)kip/(d)elete N/(a)dd 'item' 'description'][/]"
                )

            elif cmd[0] == "a" or cmd[0] == "add":
                self.new_inventory[cmd[1]] = cmd[2]
                self.printb(f"Added item '{cmd[1]}'")
                self.print_inventory()
                self.printb(
                    "[deep_sky_blue4]Does the updated inventory make sense? [KEEP/(reg)enerate/(s)kip/(d)elete N/(a)dd 'item' 'description'][/]"
                )

            elif cmd[0] == "s" or cmd[0] == "skip":
                self.state = Action_States.END
                self.skip_inventory = True
                return self.finalize()

            else:
                self.printb("[deep_sky_blue4]Command not recognised[/deep_sky_blue4]")

    def get_action_items(self):
        out = self.gstate.llm.action_items(
            self.location_description, self.gstate.inventory, self.action
        )

        self.action_items = out
        self.print_action_items()

    def generate_consequences(self):
        out = self.gstate.llm.consequences(
            self.gstate.history,
            self.location_description,
            self.action_items,
            self.action,
        )

        self.consequences = out
        self.state = Action_States.AFTER_CONSEQUENCES

        self.printb()
        self.printb(
            "[deep_sky_blue4]Do the consequences make sense? [KEEP/(reg)enerate/keep and skip to (i)nventory/keep and skip to (e)nd][/]"
        )

    def update_description(self):
        out = self.gstate.llm.update_description(
            self.location_description, self.action, self.consequences
        )

        self.new_description = out
        self.state = Action_States.AFTER_UPDATED_DESCRIPTION

        self.printb()
        self.printb(
            "[deep_sky_blue4]Would you like to keep the new description? [KEEP/(reg)enerate/(s)kip/keep and skip to (e)nd][/]"
        )

    def update_inventory(self):
        self.new_inventory = self.gstate.inventory.copy()
        try:
            new_action_items_w_empty = self.gstate.llm.update_inventory(
                self.action_items,
                self.location_description,
                self.action,
                self.consequences,
            )

            new_action_items = []
            for n in new_action_items_w_empty:
                if n.strip().lower() not in ["empty", "none", "n/a"]:
                    new_action_items += [n]

            # Replace used items
            merged = []
            for i in self.gstate.inventory:
                found_in_action = False
                for a in self.action_items:
                    if a.lower().strip() == i.lower().strip():
                        found_in_action = True
                        break

                if not found_in_action:
                    merged += [i]

            for n in new_action_items:
                merged += [n]

            self.new_inventory = merged

        except Exception as e:
            self.printb(str(e))
            self.printb("[deep_sky_blue4][No changes found][/]")
            self.new_inventory = self.gstate.inventory.copy()

        self.state = Action_States.AFTER_UPDATED_INVENTORY

        self.print_inventory()
        self.printb()
        self.printb(
            "[deep_sky_blue4]Does the updated inventory make sense? [KEEP/(reg)enerate/(s)kip/(d)elete N/(a)dd 'item' 'description'][/]"
        )

    def print_action_items(self):
        if len(self.action_items) == 0:
            self.printb("[orange4]Action items[/]: empty")
        else:
            self.printb("[orange4]Action items[/]:")
            i = 0
            for k in self.action_items:
                i += 1
                self.printb(f"({i}) {k}")

    def print_inventory(self):
        if self.skip_inventory:
            self.printb("[orange4]New inventory[/]: [skipped]")
        elif len(self.new_inventory) == 0:
            self.printb("[orange4]New inventory[/]: empty")
        else:
            self.printb("[orange4]New inventory[/]:")
            i = 0
            for k in self.new_inventory:
                i += 1
                self.printb(f"({i}) {k}")

    def finalize(self):
        events = [
            AddHistory(self.consequences),
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

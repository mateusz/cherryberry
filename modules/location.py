from enum import Enum
import orjson
import hashlib
from events import AddModule, ActivateModule, DeleteModule, ConnectLocation, AddHistory
from .action import Action
import shlex
import re
from .module import Module


class Location_States(Enum):
    START = 1


class Location(Module):
    unmanaged_fields = ["gstate", "state", "queue"]

    name: str
    description: str
    exits: object
    items: object
    state: Location_States

    help_text = """\
[u]Commands:[/]
[orange4]dark[/] - Switch to dark theme
[orange4]g,go <num>[/] - Go through the numbered exit (possibly switches to location generator)
[orange4]gn,gon,gonew "<title>" "<description of transition>"[/] - Go to a new location (switches to location generator)
[orange4]gd,god,godel <num>[/] - Delete numbered exit
[orange4]h,help[/] - This text
[orange4]i,inv,inventory[/] - Show inventory
[orange4]I <action>[/] - Perform action (switches to action generator). Write in the first person (that's why command is called I)
[orange4]l,look[/] - Repeat location description
[orange4]light[/] - Switch to light theme
"""

    @staticmethod
    def create(gstate, queue, name, description, exits, items):
        l = Location(
            gstate,
            queue,
            {
                "name": name.strip(),
                "description": description.strip(),
                "exits": exits,
                "items": items,
                "state": Location_States.START,
                "id": hashlib.md5(description.encode("utf-8")).hexdigest(),
            },
        )
        return l

    def __init__(self, gstate, queue, from_data):
        super().__init__(gstate, queue, from_data)
        self.state = Location_States(from_data["state"])

    def on_activate(self):
        self.describe()

    def on_input(self, line):
        cmd = shlex.split(line)

        if len(cmd) == 0:
            self.printb()
            self.printb(
                "[deep_sky_blue4]Command not recognised, try 'help'[/deep_sky_blue4]"
            )
        elif cmd[0] == "look" or cmd[0] == "l":
            self.describe()
        # TODO add ability to look towards an exit to see the location
        # TODO add ability to search for items
        # TODO add ability to look at items in inventory
        elif cmd[0] == "go" or cmd[0] == "g":
            exit_number = int(cmd[1]) - 1
            key = list(self.exits.keys())[exit_number]
            ex = list(self.exits.values())[exit_number]
            self.printb()
            self.printb()

            if ex.get("id", None):
                if key == "<<back>>":
                    msg = f"You backtrack towards the {ex.get('name')}."
                else:
                    msg = f"{ex.get('transition_text')}"
                self.printb(f"[italic green4]{msg}[/]")

                return [
                    AddHistory(msg),
                    ActivateModule(ex.get("id")),
                ]
            else:
                msg = f"{ex.get('transition_text')}"
                self.printb(f"[italic green4]{msg}[/]")

                l = LocationGenerator.create_from_exit(self, ex)
                return [
                    AddHistory(msg),
                    AddModule(l),
                    ActivateModule(l.id),
                ]
        elif cmd[0] == "gn" or cmd[0] == "gon" or cmd[0] == "gonew":
            ex = {"name": cmd[1], "description": cmd[2]}

            i = 1
            for k in self.exits.keys():
                if k.startswith("<<custom"):
                    n = int(re.sub(r"<<custom([0-9]*)>>", "\\1", k))
                    if n >= i:
                        i = n + 1

            self.exits[f"<<custom{i}>>"] = ex
            msg = f"You go towards the {cmd[1]}. {cmd[2]}"
            self.printb(f"[italic green4]{msg}[/]")
            l = LocationGenerator.create_from_exit(self, ex)

            return [
                AddHistory(msg),
                AddModule(l),
                ActivateModule(l.id),
            ]
        elif cmd[0] == "gd" or cmd[0] == "god" or cmd[0] == "godel":
            exit_number = int(cmd[1]) - 1
            key = list(self.exits.keys())[exit_number]
            ex = list(self.exits.values())[exit_number]

            if key == "<<back>>":
                self.printb(
                    "Cannot delete the return path, the world will collapse into singularity."
                )
            else:
                self.printb(
                    f"Deleting the exit '{ex.get('name')}'. It disappears in a wisp of smoke..."
                )
                del self.exits[key]
                if ex.get("id", None):
                    return [
                        DeleteModule(ex.get("id")),
                    ]
        elif cmd[0] == "I":
            l = Action.create(self.gstate, self.queue, self, " ".join(cmd))
            return [
                AddModule(l),
                ActivateModule(l.id),
            ]
        elif cmd[0] == "i" or cmd[0] == "inv" or cmd[0] == "inventory":
            if len(self.gstate.inventory) == 0:
                self.printb()
                self.printb("[u]Your inventory is empty[/]")
            else:
                self.printb()
                self.printb("[u]Your inventory:[/]")
                for k in self.gstate.inventory:
                    self.printb(f"[orange4]{k}[/]")

        elif cmd[0] == "help" or cmd[0] == "h":
            self.printb()
            self.printb(self.help_text)

        else:
            self.printb()
            self.printb("[deep_sky_blue4]Command not recognised, try 'help'[/]")

    def describe(self):
        self.printb()
        self.printb(f"[bold deep_pink3]--- {self.name} ---[/]")
        self.printb(f"[grey46][Ref: {self.id}][/]")
        self.printb()
        self.printb(f"{self.description}")
        self.describe_exits()
        self.describe_items()

    def describe_exits(self):
        self.printb()
        self.printb("[u]Exits:[/]")
        i = 0

        if not len(self.exits.keys()):
            self.printb("None!")
            return

        for key, ex in self.exits.items():
            i += 1
            if key == "<<back>>":
                self.printb(
                    f"[orange4]({i}) {ex.get('name')} [italic](backtrack)[/][/]"
                )
            elif ex.get("id", None):
                self.printb(
                    f"[orange4]({i}) {ex.get('name')} [italic](visited)[/][/] (already visited) - towards {ex.get('new_location_name')}"
                )
            else:
                self.printb(
                    f"[orange4]({i}) {ex.get('exit_name')}[/] - towards {ex.get('new_location_name')}"
                )

    def describe_items(self):
        self.printb()
        self.printb("[u]Items:[/]")
        i = 0

        if not len(self.items.keys()):
            self.printb("None!")
            return

        for key, it in self.items.items():
            i += 1
            self.printb(f"[orange4]({i}) {it.get('name')} [/]")

    def extra_json(self, d):
        d["state"] = self.state.value
        return d


class LocationGenerator_States(Enum):
    GET_REQUIREMENTS = 1
    AFTER_REQUIREMENTS = 2
    AFTER_DESCRIPTION = 3
    AFTER_EXITS = 4
    AFTER_ITEMS = 5


class LocationGenerator(Module):
    unmanaged_fields = ["gstate", "state", "queue", "location"]

    name: str
    requirements: str = "Abandoned house"
    from_previous_id: str
    from_previous_name: str
    from_previous_description: str
    from_exit: object
    description: str
    exits: object
    items: object
    state: LocationGenerator_States
    location: Location

    @staticmethod
    def create_from_user_input(gstate, queue, name):
        l = LocationGenerator(
            gstate,
            queue,
            {
                "name": name,
                "requirements": "",
                "from_previous_id": None,
                "from_previous_name": None,
                "from_previous_description": None,
                "from_exit": None,
                "state": LocationGenerator_States.GET_REQUIREMENTS,
                "description": "",
                "exits": {},
                "items": {},
                "id": "LocationGenerator",
            },
        )
        return l

    @staticmethod
    def create_from_exit(previous, exit):
        l = LocationGenerator(
            previous.gstate,
            previous.queue,
            {
                "name": exit.get("new_location_name"),
                "requirements": None,
                "from_previous_name": previous.name,
                "from_previous_description": previous.description,
                "from_previous_id": previous.id,
                "from_exit": exit,
                "state": LocationGenerator_States.AFTER_REQUIREMENTS,
                "description": "",
                "exits": {},
                "items": {},
                "id": "LocationGenerator",
            },
        )
        return l

    def __init__(self, gstate, queue, from_data):
        super().__init__(gstate, queue, from_data)
        self.state = LocationGenerator_States(from_data["state"])
        if self.state not in [
            LocationGenerator_States.GET_REQUIREMENTS,
            LocationGenerator_States.AFTER_REQUIREMENTS,
        ]:
            self.location = Location.create(
                self.gstate,
                self.queue,
                self.name,
                self.description,
                self.exits,
                self.items,
            )
        else:
            self.location = None

    def on_activate(self):
        if self.state == LocationGenerator_States.GET_REQUIREMENTS:
            self.printb(
                "[deep_sky_blue4]Provide requirements for the location (these will drive generation):[/]"
            )
        elif self.state == LocationGenerator_States.AFTER_REQUIREMENTS:
            self.generate_description_from_requirements()
        elif self.state == LocationGenerator_States.AFTER_DESCRIPTION:
            self.location.describe()
            self.printb()
            self.printb(
                "[deep_sky_blue4]Do you want to keep this location? [KEEP/(reg)enerate/(rew)rite][/]"
            )
        elif self.state == LocationGenerator_States.AFTER_EXITS:
            self.location.describe()
            self.printb()
            self.printb(
                "[deep_sky_blue4]Do you want to keep this list of exits? [KEEP/(reg)enerate/(s)kip][/]"
            )
        elif self.state == LocationGenerator_States.AFTER_ITEMS:
            self.location.describe()
            self.printb()
            self.printb(
                "[deep_sky_blue4]Do you want to keep this list of items? [KEEP/(reg)enerate/(s)kip][/]"
            )

    def on_input(self, line):
        if self.state == LocationGenerator_States.GET_REQUIREMENTS:
            if line == "":
                return
            self.requirements = line
            self.printb(line)
            self.printb()
            self.generate_description_from_requirements()
        elif self.state == LocationGenerator_States.AFTER_DESCRIPTION:
            if line == "reg" or line == "regenerate":
                self.description = ""
                self.exits = {}
                self.state = LocationGenerator_States.AFTER_REQUIREMENTS
                self.generate_description_from_requirements()
            elif line == "rew" or line == "rewrite":
                self.requirements = ""
                self.description = ""
                self.exits = {}
                self.state = LocationGenerator_States.GET_REQUIREMENTS
                self.printb()
                self.printb(
                    "[deep_sky_blue4]Provide requirements for the location (these will drive generation):[/]"
                )
            elif line == "" or line == "keep":
                self.generate_exits_from_description()
                self.state = LocationGenerator_States.AFTER_EXITS

        elif self.state == LocationGenerator_States.AFTER_EXITS:
            if line == "reg" or line == "regenerate":
                self.exits = {}
                self.generate_exits_from_description()
            elif line == "s" or line == "skip":
                self.exits = {}
                self.generate_items_from_description()
                self.state = LocationGenerator_States.AFTER_ITEMS
            elif line == "" or line == "keep":
                self.generate_items_from_description()
                self.state = LocationGenerator_States.AFTER_ITEMS

        elif self.state == LocationGenerator_States.AFTER_ITEMS:
            if line == "reg" or line == "regenerate":
                self.items = {}
                self.generate_items_from_description()
            elif line == "s" or line == "skip":
                self.items = {}
                return self.finalize()
            elif line == "" or line == "keep":
                return self.finalize()

    def generate_description_from_requirements(self):
        self.printb()
        self.printb(f"[bold deep_pink3]--- {self.name} ---[/]")
        self.printb()
        # TODO make one version for initial location, and the other version for subsequent location
        # Not like now, where one version is with custom requirements and other isn't (because there is no difference now!)
        if self.requirements:
            out = self.gstate.llm.generate_location(
                self.gstate.setting, self.gstate.history, self.name, self.requirements
            )
        else:
            out = self.gstate.llm.generate_location_from_exit(
                self.gstate.setting,
                self.gstate.history,
                self.from_previous_description,
                self.from_exit.get("new_location_name"),
                self.from_exit.get("new_location_description"),
            )

        self.description = out

        self.location = Location.create(
            self.gstate, self.queue, self.name, self.description, {}, {}
        )
        self.state = LocationGenerator_States.AFTER_DESCRIPTION

        self.printb()
        self.printb(
            "[deep_sky_blue4]Do you want to keep this location? [KEEP/(reg)enerate/(rew)rite][/]"
        )

    def generate_exits_from_description(self):
        self.exits = {}
        try:
            for exit in self.gstate.llm.find_exits(
                self.gstate.setting, self.description
            ):
                self.exits[exit.get("exit_name", "???")] = {
                    "exit_name": exit.get("exit_name", "???"),
                    "transition_text": exit.get("transition_text", "???"),
                    "new_location_name": exit.get("new_location_name", "???"),
                    "new_location_description": exit.get(
                        "new_location_description", "???"
                    ),
                }
        except Exception as e:
            self.printb(str(e))
            self.printb("[No exits found]")
            self.exits = {}

        self.location.exits = self.exits
        self.state = LocationGenerator_States.AFTER_EXITS
        self.location.describe_exits()

        self.printb()
        self.printb(
            "[deep_sky_blue4]Do you want to keep these exits? [KEEP/(reg)enerate/(s)kip][/]"
        )

    # TODO move this into a separate "search for items" module
    def generate_items_from_description(self):
        try:
            for item in self.gstate.llm.find_items(
                self.gstate.setting, self.description
            ):
                self.items[item.get("name", "???")] = {
                    "name": item.get("name", "???"),
                    "obtain_action": item.get("obtain_action", "???"),
                    "description": item.get("description", "???"),
                }
        except Exception as e:
            self.printb(str(e))
            self.printb("[No items found]")
            self.exits = {}

        self.location.items = self.items
        self.state = LocationGenerator_States.AFTER_ITEMS
        self.location.describe_items()

        self.printb()
        self.printb(
            "[deep_sky_blue4]Do you want to keep these items? [KEEP/(reg)enerate/(s)kip][/]"
        )

    def finalize(self):
        events = [
            DeleteModule(self.id),
            AddModule(self.location),
        ]

        if self.from_previous_id:
            events += [ConnectLocation(self.from_previous_id, self.location.id)]

        events += (ActivateModule(self.location.id),)

        return events

    def extra_json(self, d):
        d["state"] = self.state.value
        return d

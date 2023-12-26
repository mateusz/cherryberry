from enum import Enum
from events import (
    AddModule,
    ActivateModule,
    SetSetting,
    DeleteModule,
)
from .action import Action
import shlex
import re
from .module import Module
from .location import LocationGenerator


class GameInit_States(Enum):
    BEGIN = 1
    AFTER_SETTING = 2
    AFTER_STARTING_LOCATION = 3


class GameInit(Module):
    unmanaged_fields = ["gstate", "state", "queue"]

    setting: str
    starting_location: str

    @staticmethod
    def create(gstate, queue):
        l = GameInit(
            gstate,
            queue,
            {
                "setting": "",
                "starting_location": "",
                "id": "GameInit",
                "state": GameInit_States.BEGIN,
            },
        )
        return l

    def __init__(self, gstate, queue, from_data):
        super().__init__(gstate, queue, from_data)
        self.state = GameInit_States(from_data["state"])

    def on_activate(self):
        if self.state == GameInit_States.BEGIN:
            self.printb(
                "[deep_sky_blue4]Provide a one sentence setting for the game (this will drive the entire game). The setting will be appended after 'for a text adventure game like Zork, '[/]"
            )
            self.printb(
                "[gray50]Example 1: an RPG game set in a modern world torn by war, with much fighting still going on. The player is a survivor in this dark and dangerous world.[/]"
            )
            self.printb(
                "[gray50]Example 2: an RPG game set in an expansive Canadian frozen wilderness in the aftermath of a geomagnetic disaster. The player is a lone survivor facing off against the nature.[/]"
            )
        elif self.state == GameInit_States.AFTER_SETTING:
            self.printb(f"[orange4]Setting[/]: {self.setting}")
            self.printb(
                "[deep_sky_blue4]Specify a title of the starting location (this will be used in game):[/]"
            )

    def on_input(self, line):
        if self.state == GameInit_States.BEGIN:
            if line == "":
                return

            self.state = GameInit_States.AFTER_SETTING
            self.setting = line
            self.printb(line)
            self.printb()
            self.printb(
                "[deep_sky_blue4]Specify a title of the starting location (this will be used in game):[/]"
            )

        elif self.state == GameInit_States.AFTER_SETTING:
            if line == "":
                return

            self.state = GameInit_States.AFTER_STARTING_LOCATION
            self.starting_location = line
            self.printb(line)
            self.printb()

            lg = LocationGenerator.create_from_user_input(
                self.gstate, self.queue, self.starting_location
            )
            return [
                SetSetting(self.setting),
                DeleteModule(self.id),
                AddModule(lg),
                ActivateModule(lg.id),
            ]

    def extra_json(self, d):
        d["state"] = self.state.value
        return d

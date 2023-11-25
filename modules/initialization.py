from enum import Enum
import json
from events import AddModule, ActivateModule
from .location import Location

class Initialization_States(Enum):
    START = 1
    AFTER_INITIAL_LOCATION = 2

class Initialization():

    def __init__(self, llm, starter_data=None, from_data=None):
        self.name = "Initialization"
        self.id = self.name
        self.llm=llm
        if from_data:
            self.state = Initialization_States(from_data["state"])
            self.starter_data=from_data["starter_data"]
            self.initial_location_description = from_data["initial_location_description"]
        else:
            self.state = Initialization_States.START
            self.starter_data=starter_data
            self.initial_location_description = ""
    
    def on_activate(self):
        print("Welcome to Cherryberry, an interactive text adventure!")
        print("")
        print(f"Press ENTER to generate initial location")

    def on_input(self, line):
        if self.state==Initialization_States.START:
            try:
                l = Location.create_from_requirements("Adventure awaits!", self.llm, self.starter_data)
                self.state = Initialization_States.AFTER_INITIAL_LOCATION
                return [
                    AddModule(l),
                    ActivateModule(l.id),
                ]
            except Exception as exc:
                print(exc)
                print("Failed. Press ENTER to try again")

        return []
    
    def toJSON(self):
        return json.dumps({
            "id": self.id,
            "name": self.name,
            "class": self.__class__.__name__,
            "state": self.state.value,
            "starter_data": self.starter_data,
            "initial_location_description": self.initial_location_description 
        }, sort_keys=True, indent=4)
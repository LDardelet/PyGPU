import numpy as np

import Components
from Values import Colors, Params
from Console import ConsoleWidget, Log, LogSuccess, LogWarning, LogError

class ComponentsHandler:
    def __init__(self):
        GroupClass.Handler = self

        self.MaxValue = 0
        self.Dict = {}
        self.ComponentsLimits = np.array([[0,0], [0.,0]])
        self.Map = np.zeros((Params.Board.Size, Params.Board.Size, 9), dtype = int)

        self.Groups = {} # Groups shre wire transmissions

    def Register(self, Locations, NewComponent, NewConnexionsLocations):
        Values = self.Map[Locations[:,0], Locations[:,1], Locations[:,2]]
        if (Values != 0).any(): # TODO : Ask for wire bridges
            LogWarning(f"Unable to register the new component, due to positions {Locations[np.where(Values != 0), :].tolist()}")
            return False

        self.SetComponent(NewComponent, Locations)
        for Location in Locations:
            ConnID = self.Map[Location[0],Location[1],-1]
            if ConnID and self.Dict[ConnID].Displayed: # Start by linking existing connexions on the advertized locations
                self.Dict[ConnID].Update(self.Map[Location[0],Location[1],:])

        for Location in NewConnexionsLocations: # Add automatically created connexions
            ConnID = self.Map[Location[0],Location[1],-1]
            if ConnID:
                if not self.Dict[ConnID].LinkedTo(NewComponent.ID):# If NewConnexionsLocations should already be within Locations, hidden connexions would have been avoided due to previous method
                    self.Dict[ConnID].Update(self.Map[Location[0],Location[1],:])
            else:
                self.AddConnexion(Location) # If not, we create it
        return True

    def SetComponent(self, Component, AdvertisedLocations): # Sets the ID of a component and stores it. Does not handle links.
        self.MaxValue += 1
        Component.ID = self.MaxValue
        self.Dict[Component.ID] = Component
        for x, y, theta in AdvertisedLocations:
            Component.AdvertisedLocations.add((x,y,theta))
            self.Map[x,y,theta] = Component.ID

    def DestroyComponent(self, ID): # Completely removes the component by its ID. Does not handle links.
        Component = self.Dict.pop(ID)
        for x, y, theta in Component.AdvertisedLocations:
            self.Map[x,y,theta] = 0
        Component.destroy()

    def ToggleConnexion(self, Location):
        if self.Map[Location[0], Location[1],-1]:
            self.RemoveConnexion(Location)
        else:
            self.AddConnexion(Location)
    def AddConnexion(self, Location):
        Column = self.Map[Location[0], Location[1],:]
        if Column[-1]:
            LogError(f"Connexion at {Location} already exists")
            return
        NewConnexion = Components.Connexion(Location, Column)
        self.SetComponent(NewConnexion, ((Location[0], Location[1], -1),))
        for ID in Column[:-1]:
            if ID:
                self.Link(ID, NewConnexion.ID)
    def RemoveConnexion(self, Location):
        Column = self.Map[Location[0], Location[1],:]
        if Column[-1]:
            LogError(f"No connexion to remove at {Location}")
            return
        IDs = set()
        for ID in Column[:-1]:
            if ID:
                if type(self.Dict[ID]) != Components.Wire:
                    LogWarning("Cannot remove connexion as it is linked to a component")
                    return
                IDs.add(ID)
        ConnID = Column[-1]
        for ID in IDs:
            self.BreakLink(ID, ConnID)
        self.DestroyComponent(ConnID)

    def Link(self, ID1, ID2): # Must be here to ensure symmetric props
        self.Dict[ID1].Links.add(ID2)
        self.Dict[ID2].Links.add(ID1)
    def BreakLink(self, ID1, ID2): # Must be here to ensure symmetric props
        try:
            self.Dict[ID1].Links.remove(ID2)
        except KeyError:
            LogError(f"ID {ID2} was not advertized for ID {ID1} (1)")
        try:
            self.Dict[ID2].Links.remove(ID1)
        except KeyError:
            LogError(f"ID {ID1} was not advertized for ID {ID2} (2)")

    def Repr(self, Location):
        NWires = 0
        Data = []
        Keypoint = False
        Column = self.Map[Location[0], Location[1],:]
        for ID in Column[:-1]:
            if ID:
                Component = self.Dict[ID]
                if type(Component) == Components.Wire:
                    NWires += 1
                else:
                    Keypoint = True
                    Data.append(Component.CName)
        if not Data and NWires == 0:
            return ""

        if NWires:
            Data = [Components.Wire.CName+'s'*(NWires >= 3)] + Data
        if Keypoint or (NWires >= 3 and Column[-1]):
            Data += ["(connected)"]
        elif not Keypoint and (NWires >= 3 and not Column[-1]):
            Data += ["(isolated)"]
        return ', '.join(Data)

    def HasItem(self, Location):
        return self.Map[Location[0], Location[1], :8].any()

class GroupClass:
    Handler = None
    def __init__(self, BaseComponent): # To avoid creating useless new IDs, a group ID is define by the ID of its first component. May lead to issues later on, but unlikely.
        self.ID = BaseComponent.ID
        self.Components = {BaseComponent}

    def Merge(self, Group): # We keep the lowest ID possible.
        if self.ID > Group.ID:
            self, Group = Group, self # May not work, not checked yet
        
        for Component in Group.Components:
            Component.Group = self.ID
        self.Elements.update(Group.Components)
        del self.Handler.Groups[Group.ID]

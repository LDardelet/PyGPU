import numpy as np

import Components
from Values import Colors, Params, LevelsNames
from Console import Log, LogSuccess, LogWarning, LogError
import DefaultLibrary

class ComponentsHandler:
    def __init__(self):
        GroupClass.Handler = self
        Components.ComponentBase.Handler = self

        self.MaxValue = 0
        self.Components = {}
        self.Casings = {}
        self.ComponentsLimits = np.array([[0,0], [0.,0]])
        self.Map = np.zeros((Params.Board.Size, Params.Board.Size, 9), dtype = int)

        self.Highlighed = None
        self.Groups = {} # Groups share wire transmissions

        self.LiveUpdate = True

    def Register(self, NewComponent, MustCheck = True):
        if MustCheck and not self.CheckRoom(NewComponent):
            LogWarning(f"Unable to register the new component, due to position conflicts")
            return False

        self.SetComponent(NewComponent)
        for x,y,_ in NewComponent.AdvertisedLocations:
            ConnID = self.Map[x,y,-1]
            if ConnID == NewComponent.ID: # Need to check for location forbidden connexions
                continue
            if ConnID and self.Components[ConnID].Displayed: # Start by linking existing connexions on the advertized locations
                self.Components[ConnID].UpdateConnexions(self.Map[x,y,:])
                self.AddLink(NewComponent.ID, ConnID)

        for x,y in NewComponent.AdvertisedConnexions: # Add automatically created connexions, in particular to existing hidden connexions
            ConnID = self.Map[x,y,-1]
            if ConnID == NewComponent.ID: # Need to check for location forbidden connexions
                continue
            if ConnID:
                if not self.Components[ConnID].LinkedTo(NewComponent.ID):# If NewConnexion should already be within NewLocations, hidden connexions would have been avoided due to previous method
                    self.Components[ConnID].UpdateConnexions(self.Map[x,y,:])
                    self.AddLink(NewComponent.ID, ConnID)
            else:
                self.AddConnexion((x,y)) # If not, we create it
        return True

    def CheckRoom(self, NewComponent):
        NewLocations = NewComponent.AdvertisedLocations
        Values = self.Map[NewLocations[:,0], NewLocations[:,1], NewLocations[:,2]]
        return (Values == 0).all() # TODO : Ask for wire bridges
            #LogWarning(f"Unable to register the new component, due to positions {NewLocations[np.where(Values != 0), :].tolist()}")

    def SetComponent(self, Component): # Sets the ID of a component and stores it. Does not handle links.
        self.MaxValue += 1
        Component.ID = self.MaxValue
        self.Components[Component.ID] = Component
        Component.Group = GroupClass(Component)
        for x, y, theta in Component.AdvertisedLocations:
            self.Map[x,y,theta] = Component.ID
        if isinstance(Component, Components.CasedComponent):
            self.Casings[Component.ID] = Component

    def DestroyComponent(self, ID): # Completely removes the component by its ID. Does not handle links.
        Component = self.Components.pop(ID)
        for x, y, theta in Component.AdvertisedLocations:
            self.Map[x,y,theta] = 0
        Component.destroy()

    def ToggleConnexion(self, Location):
        if self.Map[Location[0], Location[1],-1] and isinstance(self.Components[self.Map[Location[0], Location[1],-1]], Components.Connexion): # Second check for pin bases
            self.RemoveConnexion(Location)
        else:
            self.AddConnexion(Location)
    def AddConnexion(self, Location):
        Column = self.Map[Location[0], Location[1],:]
        if Column[-1]:
            LogError(f"Connexion at {Location} already exists")
            return
        NewConnexion = Components.Connexion(Location, Column)
        self.SetComponent(NewConnexion)
        for ID in Column[:-1]:
            if ID:
                if NewConnexion.Group is None:
                    self.Components[ID].Group.AddComponent(NewConnexion)
                self.AddLink(ID, NewConnexion.ID)
    def RemoveConnexion(self, Location):
        Column = self.Map[Location[0], Location[1],:]
        if Column[-1]:
            LogError(f"No connexion to remove at {Location}")
            return
        IDs = set()
        for ID in Column[:-1]:
            if ID:
                if type(self.Components[ID]) != Components.Wire:
                    LogWarning("Cannot remove connexion as it is linked to a component")
                    return
                IDs.add(ID)
        ConnID = Column[-1]
        for ID in IDs:
            self.BreakLink(ID, ConnID)
        self.DestroyComponent(ConnID)

    def AddLink(self, ID1, ID2): # Must be here to ensure symmetric props
        self.Components[ID1].Links.add(ID2)
        self.Components[ID2].Links.add(ID1)
        if self.Components[ID1].Group != self.Components[ID2].Group:
            self.Components[ID1].Group.Merge(self.Components[ID2].Group)

    def BreakLink(self, ID1, ID2): 
        try:
            self.Components[ID1].Links.remove(ID2)
        except KeyError:
            LogError(f"ID {ID2} was not advertized for ID {ID1} (1)")
        try:
            self.Components[ID2].Links.remove(ID1)
        except KeyError:
            LogError(f"ID {ID1} was not advertized for ID {ID2} (2)")

    def MoveHighlight(self, Location):
        Groups = list({self.Components[ID].Group for ID in self.Map[Location[0], Location[1],:-1] if ID})
        if Groups:
            return self.SwitchHighlight(Groups[0])
        else:
            for Component in self.Casings.values():
                if Component.Contains(Location):
                    return self.SwitchHighlight(Component)
        self.SwitchHighlight(None)

    def SwitchHighlight(self, Item):
        if Item == self.Highlighed:
            return
        if not self.Highlighed is None:
            self.Highlighed.Highlight(False)
        self.Highlighed = Item
        if not Item is None:
            self.Highlighed.Highlight(True)

    def Repr(self, Location):
        NWires = 0
        Data = []
        Keypoint = False
        Column = self.Map[Location[0], Location[1],:]

        Groups = {}
        for ID in Column[:-1]:
            if ID:
                Component = self.Components[ID]
                if Component.Group in Groups:
                    Groups[Component.Group].add(Component)
                else:
                    Groups[Component.Group] = {Component}
        if not Groups:
            return ""

        return ', '.join([f'Group {Group.ID} : '+ ', '.join([str(Component) for Component in Components])+f' ({LevelsNames[Group.Value]})' for Group, Components in Groups.items()]) + (len(Groups)>1)*' (isolated)'

    def Wired(self, Location):
        for ID in self.Map[Location[0], Location[1], :8]:
            if ID and (isinstance(self.Components[ID], Components.Wire) or isinstance(self.Components[ID], Components.ComponentPin)):
                return True
        return False
    def HasItem(self, Location):
        return self.Map[Location[0], Location[1], :8].any()

class GroupClass:
    Handler = None # Allows to handles group storage
    def __init__(self, BaseComponent): # To avoid creating useless new IDs, a group ID is define by the ID of its first component. May lead to issues later on, but unlikely.
        self.ID = BaseComponent.ID
        self.Handler.Groups[self.ID] = self
        BaseComponent.Group = self
        self.Components = {BaseComponent}

        self.HighlightPlots = list(BaseComponent.HighlightPlots)

        self.Value = None
        self.SetBy = None

    def Merge(self, Group): # We keep the lowest ID possible.
        #if self.ID > Group.ID:
        #    self, Group = Group, self # May not work, not checked yet. Removed for now
        self.HighlightPlots += Group.HighlightPlots
        for Component in Group.Components:
            Component.Group = self
        self.Components.update(Group.Components)
        del self.Handler.Groups[Group.ID]

    def AddComponent(self, Component):
        Component.Group = self
        self.Components.add(Component)
        self.HighlightPlots += Component.HighlightPlots

    def SetValue(self, Value, Component):
        if not self.SetBy is None and Component != self.SetBy:
            LogWarning(f"Group {self.ID} set by {Component} and {self.SetBy}")
        self.SetBy = Component
        self.Value = Value
        self.UpdateGroupColor()

    def UpdateGroupColor(self): # May be more efficient to update plots directly. However, it forbids hot board modifications
        for Component in self.Components:
            Component.Update()

    def Highlight(self, var):
        for Component in self.Components:
            Component.Highlight(var)

    def __repr__(self):
        return f"Group {self.ID}"

# Component template signature :
# (Location, West, East, North=None, South=None, Callback = None, Schematics = None, ForceWidth = None, ForceHeight = None)

class CGroup:
    def __init__(self, GName, GComponents = {}):
        self.Name = GName
        self.Components = []
        for Name, Values in GComponents.items():
            if Name in self.__dict__:
                LogWarning(f"Component name {Name} already exists in this library")
                continue
            self.Components.append(Name)
            if isinstance(Values, type(Components.ComponentBase)):
                self.__dict__[Name] = Values
            else:
                self.AddComponentClass(Name, Values)

    def AddComponentClass(self, Name, Values):
        try:
            InputPinsDef, OutputPinsDef, Callback, Schematics, ForceWidth, ForceHeight, DisplayPinNumbering, Symbol = Values
            PinIDs = set()
            for PinLocation, PinName in InputPinsDef + OutputPinsDef:
                if PinLocation in PinIDs:
                    raise ValueError
        except ValueError:
            LogWarning(f"Unable to load component {Name} from its definition")
            return
        self.__dict__[Name] = type(Name, 
                                   (Components.CasedComponent, ), 
                                   {
                                       '__init__': Components.CasedComponent.__init__,
                                       'CName': Name,
                                       'InputPinsDef'    : InputPinsDef,
                                       'OutputPinsDef'    : OutputPinsDef,
                                       'Callback'   : Callback,
                                       'Schematics' : Schematics,
                                       'ForceWidth' : ForceWidth,
                                       'ForceHeight': ForceHeight,
                                       'DisplayPinNumbering':DisplayPinNumbering,
                                       'Symbol':Symbol,
                                   })
class CLibrary:
    ComponentBase = Components.ComponentBase
    def __init__(self):
        self.Groups = []
        self.AddGroup(CGroup('Standard', DefaultLibrary.Definitions))
        self.Wire = Components.Wire

    def AddGroup(self, Group):
        self.__dict__[Group.Name] = Group
        self.Groups.append(Group.Name)

    def IsWire(self, C): # Checks if class or class instance
        return C == Components.Wire or isinstance(C, Components.Wire)

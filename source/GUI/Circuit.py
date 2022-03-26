import numpy as np

import Components
from Values import Colors, Params, LevelsNames
from Console import Log, LogSuccess, LogWarning, LogError
import DefaultLibrary
from Storage import StorageItem

class ComponentsHandler(StorageItem):
    LibRef = "ComponentsHandler"
    def __init__(self):
        # Dynamic Data
        self.Casings = {}
        self.LiveUpdate = True
        self.Map = np.zeros((Params.Board.Size, Params.Board.Size, 9), dtype = int)

        StorageItem.__init__(self)
        # Saved Data
        self.MaxID = 0
        self.Components = {}
        self.Groups = {} # Groups share wire transmissions
        self._StoredAttributes.add('MaxID')
        self._StoredAttributes.add('Components')
        self._StoredAttributes.add('Groups')

    def NewGroup(self, Comp):
        Group = GroupC(Comp)
        self.Groups[Group.ID] = Group
        return Group

    def Register(self, NewComponent):
        if not NewComponent.CanFix:
            return False
        if not self.CheckRoom(NewComponent):
            LogWarning(f"Unable to register the new component, due to position conflicts")
            return False
        for Child in NewComponent.Children:
            if not Child.CanFix:
                return False
            if not self.CheckRoom(Child):
                LogWarning(f"Unable to register the new component, due to child {Child} position conflict")
                return False

        for Child in NewComponent.Children:
            self.SetComponent(Child)
            self.LinkToGrid(Child)
            Child.Fix()
        self.SetComponent(NewComponent)
        self.LinkToGrid(NewComponent)
        NewComponent.Fix()

        if self.LiveUpdate:
            NewComponent() 

        return True

    def LinkToGrid(self, NewComponent):
        for x,y,_ in NewComponent.AdvertisedLocations:
            ConnID = self.Map[x,y,-1]
            if ConnID == NewComponent.ID: # Need to check for location forbidden connexions
                continue
            if ConnID and self.Components[ConnID].Displayed: # Start by linking existing shown connexions on the advertized locations
                self.Components[ConnID].UpdateConnexions(self.Map[x,y,:])
                self.AddLink(NewComponent.ID, ConnID)
        for x,y in NewComponent.AdvertisedConnexions: # Add automatically created connexions, in particular to existing hidden connexions
            ConnID = self.Map[x,y,-1]
            if ConnID == NewComponent.ID: # Need to check for location forbidden connexions
                continue
            if ConnID:
                if not self.Components[ConnID].LinkedTo(NewComponent.ID):# If NewConnexion should already be within NewLocations, hidden connexions are avoided in previous method
                    self.Components[ConnID].UpdateConnexions(self.Map[x,y,:])
                    self.AddLink(NewComponent.ID, ConnID)
            else:
                self.AddConnexion((x,y)) # If not, we create it

    def CheckRoom(self, NewComponent):
        NewLocations = NewComponent.AdvertisedLocations
        Values = self.Map[NewLocations[:,0], NewLocations[:,1], NewLocations[:,2]]
        return (Values == 0).all() # TODO : Ask for wire bridges
            #LogWarning(f"Unable to register the new component, due to positions {NewLocations[np.where(Values != 0), :].tolist()}")

    def SetComponent(self, Component, ID = None): # Sets the ID of a component and stores it. Does not handle links. ID can be specified to load saved data
        if ID is None:
            self.MaxID += 1
            Component.ID = self.MaxID
        else:
            if ID in self.Components:
                raise ValueError
            Component.ID = ID

        self.Components[Component.ID] = Component
        #Component.Group = self.NewGroup(Component) # Odd line, must probably be deleted
        for x, y, theta in Component.AdvertisedLocations:
            self.Map[x,y,theta] = Component.ID
        if isinstance(Component, Components.CasedComponent):
            self.Casings[Component.ID] = Component
            if Params.Board.CasingsOwnPinsBases:
                Component.Group = self.NewGroup(Component)
            else:
                Component.Group = CasingGroup
        else:
            Component.Group = self.NewGroup(Component)

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
            del self.Groups[self.Components[ID1].Group.Merge(self.Components[ID2].Group)]

    def BreakLink(self, ID1, ID2): 
        try:
            self.Components[ID1].Links.remove(ID2)
        except KeyError:
            LogError(f"ID {ID2} was not advertized for ID {ID1} (1)")
        try:
            self.Components[ID2].Links.remove(ID1)
        except KeyError:
            LogError(f"ID {ID1} was not advertized for ID {ID2} (2)")

    def CursorGroups(self, Location):
        return list({self.Components[ID].Group for ID in self.Map[Location[0], Location[1],:-1] if ID})
    def CursorComponents(self, Location):  # We remove ComponentPin from single component highlight as nothing can be done with them alone
        return list({self.Components[ID] for ID in self.Map[Location[0], Location[1],:-1] if (ID and not isinstance(self.Components[ID], Components.ComponentPin))})
    def CursorCasings(self, Location):
        return list({Component for Component in self.Casings.values() if Component.Contains(Location)})

    def GroupsInfo(self, Location):
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

        #return ', '.join([f'Group {Group.ID} : '+ ', '.join([str(Component) for Component in Components])+f' ({LevelsNames[Group.Value]})' for Group, Components in Groups.items()]) + (len(Groups)>1)*' (isolated)'
        return ', '.join([f'{Group}' + ': '*bool(Group.__repr__())+ ', '.join([str(Component) for Component in Components]) for Group, Components in Groups.items()]) + (len(Groups)>1)*' (isolated)'

    def CasingsInfo(self, Location):
        return ', '.join([str(Casing) for Casing in self.CursorCasings(Location)])

    def Wired(self, Location):
        for ID in self.Map[Location[0], Location[1], :8]:
            if ID and (isinstance(self.Components[ID], Components.Wire) or isinstance(self.Components[ID], Components.ComponentPin)):
                return True
        return False
    def HasItem(self, Location):
        return self.Map[Location[0], Location[1], :8].any()

    @property
    def ComponentsLimits(self):
        PresenceMap = self.Map.any(axis = 2)
        Limits = np.zeros((2,2), dtype = int)
        xPresMap = PresenceMap.any(axis = 1)
        Limits[0,:] = xPresMap.argmin(), xPresMap.argmax()
        yPresMap = PresenceMap.any(axis = 0)
        Limits[1,:] = yPresMap.argmin(), yPresMap.argmax()
        Limits[np.where(Limits > Params.Board.Max)] -= Params.Board.Size
        return Limits

class GroupC(StorageItem):
    LibRef = "Group"
    def __init__(self, BaseComponent = None): # To avoid creating useless new IDs, a group ID is define by the ID of its first component. May lead to issues later on, but unlikely.
        if not BaseComponent is None:
            BaseComponent.Group = self
            self.Components = {BaseComponent}
            self.ID = BaseComponent.ID
            self.HighlightPlots = list(BaseComponent.HighlightPlots)
        else:
            self.Components = {}
            self.ID = None
            self.HighlightPlots = []

        StorageItem.__init__(self)
        self._StoredAttributes.add('ID')
        self._StoredAttributes.add('Components')
        self._StoredAttributes.add('Value')
        self._StoredAttributes.add('SetBy')


        self.Value = None
        self.SetBy = None

    def Merge(self, Group): 
        self.HighlightPlots += Group.HighlightPlots
        for Component in Group.Components:
            Component.Group = self
        self.Components.update(Group.Components)

        if self.IsSet:
            if Group.IsSet:
                self.DualSetWarning(Group.SetBy)
            else:
                self.SetValue(self.Value, self.SetBy)
        else:
            if Group.IsSet:
                self.SetValue(Group.Value, Group.SetBy)
        return Group.ID

    def AddComponent(self, Component):
        Component.Group = self
        self.Components.add(Component)
        self.HighlightPlots += Component.HighlightPlots

    def SetValue(self, Value, Component):
        if not self.SetBy is None and Component != self.SetBy:
            self.DualSetWarning(Component)
            return
        self.SetBy = Component
        self.Value = Value
        self.UpdateGroupColor()

    def DualSetWarning(self, Component):
        LogWarning(f"Group {self.ID} set by {Component} and {self.SetBy}")

    @property
    def IsSet(self):
        return not self.Value is None

    def UpdateGroupColor(self): # May be more efficient to update plots directly. However, it forbids hot board modifications
        for Component in self.Components:
            Component.Update()

    def Highlight(self, var):
        for Component in self.Components:
            if type(Component) != Components.ComponentPin:
                Component.Highlight(var)
    def Select(self, var):
        for Component in self.Components:
            if type(Component) != Components.ComponentPin:
                Component.Select(var)
    def Clear(self):
        for Component in self.Components:
            Component.Clear()

    def __repr__(self):
        return f"Group {self.ID} ({LevelsNames[self.Value]})"
    def __len__(self):
        return len(self.Components)

class CasingGroupC:
    Value = None
    def __repr__(self):
        return ""
CasingGroup = CasingGroupC()

# Component template signature :
# (InputPins, OutputPins, Callback, Schematics, ForceWidth, ForceHeight, DisplayPinNumbering, Symbol)

class BookC:
    def __init__(self, Name, BookComponents = {}):
        self.Name = Name
        self.Components = []
        for CompName, CompData in BookComponents.items():
            if CompName in self.__dict__:
                LogWarning(f"Component name {CompName} already exists in this book")
                continue
            self.Components.append(CompName)
            if isinstance(CompData, type(Components.ComponentBase)):
                self.__dict__[CompName] = CompData
                CompData.Book = self
            else:
                self.AddComponentClass(CompName, CompData)
    def __repr__(self):
        return self.Name

    def AddComponentClass(self, CompName, Values):
        try:
            InputPinsDef, OutputPinsDef, Callback, Schematics, ForceWidth, ForceHeight, DisplayPinNumbering, Symbol = Values
            PinIDs = set()
            for PinLocation, PinName in InputPinsDef + OutputPinsDef:
                if PinLocation in PinIDs:
                    raise ValueError
        except ValueError:
            LogWarning(f"Unable to load component {Name} from its definition")
            return
        self.__dict__[CompName] = type(CompName, 
                                   (Components.CasedComponent, ), 
                                   {
                                       '__init__': Components.CasedComponent.__init__,
                                       'CName': CompName,
                                       'Book': self.Name,
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
    ComponentBase = Components.ComponentBase # Used to transmit Ax reference
    def __init__(self):
        StorageItem.Library = self

        self.Books = []
        self.Special = {}
        self.AddBook(BookC('Standard', DefaultLibrary.Definitions))
        self.Wire = Components.Wire

        self.AddSpecialStorageClass(Components.StateHandler)
        self.AddSpecialStorageClass(Components.Connexion)
        self.AddSpecialStorageClass(GroupC)
        self.AddSpecialStorageClass(ComponentsHandler)

    def AddBook(self, Book):
        self.__dict__[Book.Name] = Book
        self.Books.append(Book.Name)

    def IsWire(self, C): # Checks if class or class instance
        return C == Components.Wire or isinstance(C, Components.Wire)

    def AddSpecialStorageClass(self, Class):
        if '.' in Class.LibRef:
            LogWarning("Special storage class contains forbidden character '.'")
        self.Special[Class.LibRef] = Class
    def __getitem__(self, LibRef):
        if '.' in LibRef:
            BName, CName = LibRef.split('.')
            return getattr(getattr(self, BName), CName)
        else:
            return self.Special[LibRef]

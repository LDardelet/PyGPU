import numpy as np

import Components as ComponentsModule
from Values import Colors, Params, Levels
from Console import Log, LogSuccess, LogWarning, LogError
import DefaultLibrary
from Storage import StorageItem, Modifies

class ComponentsHandlerC(StorageItem):
    LibRef = "ComponentsHandler"
    def __init__(self):
        self.StoredAttribute('MaxID', 0)
        self.StoredAttribute('Components', {})
        self.StoredAttribute('Groups', {})
        self.StoredAttribute('Casings', {})
        self.Start()

    def Start(self):
        self.Map = np.zeros((Params.Board.Size, Params.Board.Size, 9), dtype = int)
        for Component in self.Components.values():
            self.RegisterMap(Component)

        GroupC.Handler = self
        self.LiveUpdate = True
        self.Ready = True
        self.AwaitingUpdates = set()

    def Building(func):
        def RegisterBuilding(self, *args, **kwargs):
            self.Ready = False
            output = func(self, *args, **kwargs)
            if self.LiveUpdate:
                self.SolveRequests()
            self.Ready = True
            return output
        return RegisterBuilding

    def ComputeChain(self):
        Log("Updating chain")

    def UpdateRequest(self, Component):
        if not self.LiveUpdate:
            return
        if self.Ready:
            Component()
        else:
            self.AwaitingUpdates.add(Component)

    def SolveRequests(self):
        UpdatedComponents = set()
        while self.AwaitingUpdates:
            Component = self.AwaitingUpdates.pop()
            if Component in UpdatedComponents:
                LogWarning(f"{Component} entered an unstable recursive loop")
                break
            Component()
            UpdatedComponents.add(Component)

    @Modifies
    @Building
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

        if NewComponent.ID is None: # Placed here to avoid resetting it
            self.Remember(NewComponent)

        self.SetComponent(NewComponent)
        NewComponent.Fix()

        self.UpdateRequest(NewComponent)    
        return True

    @Modifies
    @Building
    def Remove(self, Components):
        print(f"Attempting to remove {Components}")
        self.UnsetComponents(Components)
        for Component in Components:
            self.Forget(Component)
            Component.destroy()

    def CheckRoom(self, NewComponent):
        NewLocations = NewComponent.AdvertisedLocations
        IDs = self.Map[NewLocations[:,0], NewLocations[:,1], NewLocations[:,2]]
        return (IDs == 0).all() # TODO : Ask for wire bridges
            #LogWarning(f"Unable to register the new component, due to positions {NewLocations[np.where(IDs != 0), :].tolist()}")

    def SetComponent(self, Component): # Sets the ID of a component and stores it. Handles links through LinkToOthers.
        for Child in Component.Children:
            self.SetComponent(Child)

        self.RegisterMap(Component)
        if not isinstance(Component, ComponentsModule.CasedComponentC) or Params.Board.CasingsOwnPinsBases:
            GroupC(Component)
        else:
            CasingGroupC(Component)
        self.LinkToOthers(Component)
    def UnsetComponents(self, InputComponents):
        InputComponents = set(InputComponents)
        Components = set()
        while InputComponents: # Incase of children nesting
            Component = InputComponents.pop()
            Components.add(Component)
            for Child in Component.Children:
                if Child not in Components:
                    InputComponents.add(Child)
        
        AffectedConnexions = self.GetConnexions(Components)
        for Component in Components:
            for LinkedComponent in set(Component.Links):
                self.Unlink(Component, LinkedComponent)
            self.UnregisterMap(Component)
        while Components:
            print(f"Components remaining: {Components}")
            Component = Components.pop()
            Group = Component.Group
            if not Group is None: # Happens if the component was the only one of its group, typically
                GroupComponents = {Component}.union(Components.intersection(Group.Components))
                Components.difference_update(GroupComponents)
                print(f"Splitting {Group} with {GroupComponents}")
                Group.Split(GroupComponents)
        for Connexion in AffectedConnexions:
            Connexion.UpdateColumn(self.Map[Connexion.Location[0], Connexion.Location[1], :])
            if Connexion.ShouldBeRemoved:
                self.RemoveConnexion(Connexion)

    def Remember(self, Component):
        for Child in Component.Children:
            self.Remember(Child)
        
        self.MaxID += 1
        Component.ID = self.MaxID
        self.Components[Component.ID] = Component
        if isinstance(Component, ComponentsModule.CasedComponentC):
            self.Casings[Component.ID] = Component
    def Forget(self, Component):
        for Child in Component.Children:
            self.Forget(Child)

        del self.Components[Component.ID]
        if isinstance(Component, ComponentsModule.CasedComponentC):
            del self.Casings[Component.ID]

    def LinkToOthers(self, NewComponent):
        if isinstance(NewComponent, ComponentsModule.ConnexionC):
            for ID in NewComponent.Column:
                if ID:
                    self.Link(self.Components[ID], NewComponent)
            return
        for x,y,_ in NewComponent.AdvertisedLocations:
            ConnID = self.Map[x,y,-1]
            if ConnID == NewComponent.ID: # Need to check for location forbidden connexions
                continue
            if ConnID:
                Connexion = self.Components[ConnID]
                Connexion.UpdateColumn(self.Map[x,y,:])
                self.Link(NewComponent, Connexion)
        for x,y in NewComponent.AdvertisedConnexions: # Add automatically created connexions, in particular to existing hidden connexions
            ConnID = self.Map[x,y,-1]
            if ConnID == NewComponent.ID: # Need to check for location forbidden connexions
                continue
            if ConnID:
                Connexion = self.Components[ConnID]
                if not Connexion.LinkedTo(NewComponent):# If NewConnexion should already be within NewLocations, hidden connexions are avoided in previous method
                    Connexion.UpdateColumn(self.Map[x,y,:])
                    self.Link(NewComponent, Connexion)
            else:
                self.AddConnexion((x,y)) # If not, we create it

    @staticmethod
    def Link(C1, C2):
        C1.Links.add(C2)
        C2.Links.add(C1)
        if C1.Group != C2.Group:
            C1.Group.Merge(C2.Group)
    @staticmethod
    def Unlink(C1, C2):
        C1.Links.remove(C2)
        C2.Links.remove(C1)

    def RegisterMap(self, Component):
        for x, y, theta in Component.AdvertisedLocations:
            self.Map[x,y,theta] = Component.ID
    def UnregisterMap(self, Component):
        for x, y, theta in Component.AdvertisedLocations:
            self.Map[x,y,theta] = 0

    @Modifies
    @Building
    def ToggleConnexion(self, Location):
        if self.Map[Location[0], Location[1],-1]:
            Connexion = self.Components[self.Map[Location[0], Location[1],-1]]
            if isinstance(Connexion, ComponentsModule.ConnexionC): # Second check for pin bases
                self.RemoveConnexion(Connexion)
        else:
            self.AddConnexion(Location)

    def AddConnexion(self, Location):
        NewConnexion = ComponentsModule.ConnexionC(Location, self.Map[Location[0], Location[1],:])
        self.Remember(NewConnexion)
        self.SetComponent(NewConnexion)
    def RemoveConnexion(self, Connexion):
        if not Connexion.CanBeRemoved:
            LogWarning("Attempting to removed a fixed connexion")
            return
        self.UnsetComponents({Connexion})
        Connexion.destroy()
        del self.Components[Connexion.ID]

    def GetConnexions(self, Components):
        Connexions = set()
        for Component in Components:
            if isinstance(Component, ComponentsModule.ConnexionC):
                continue
            for LinkedComponent in Component.Links:
                if isinstance(LinkedComponent, ComponentsModule.ConnexionC):
                    Connexions.add(LinkedComponent)
        return Connexions

    def CursorGroups(self, Location):
        return list({self.Components[ID].Group for ID in self.Map[Location[0], Location[1],:-1] if ID})
    def CursorComponents(self, Location):  # We remove ComponentPin from single component highlight as nothing can be done with them alone
        return list({self.Components[ID] for ID in self.Map[Location[0], Location[1],:-1] if (ID and not isinstance(self.Components[ID], ComponentsModule.ComponentPinC))})
    def CursorCasings(self, Location):
        return list({Component for Component in self.Casings.values() if Location in Component})
    def CursorConnected(self, Location):
        return bool(self.Map[Location[0], Location[1],-1])
    def CanToggleConnexion(self, Location):
        if not self.CursorConnected(Location):
            return (self.Map[Location[0], Location[1],:-1] != 0).sum() > 3 
        else:
            ID = self.Map[Location[0], Location[1], -1]
            C = self.Components[self.Map[Location[0], Location[1], -1]]
            if not isinstance(C, ComponentsModule.ConnexionC):
                return False
            return C.CanBeRemoved

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

        #return ', '.join([f'Group {Group.ID} : '+ ', '.join([str(Component) for Component in Components])+f' ({Levels.Names[Group.Level]})' for Group, Components in Groups.items()]) + (len(Groups)>1)*' (isolated)'
        return ', '.join([f'{Group}' + ': '*bool(Group.__repr__())+ ', '.join([str(Component) for Component in Components]) for Group, Components in Groups.items()]) + (len(Groups)>1)*' (isolated)'

    def CasingsInfo(self, Location):
        return ', '.join([str(Casing) for Casing in self.CursorCasings(Location)])

    def Wired(self, Location):
        for ID in self.Map[Location[0], Location[1], :8]:
            if ID and (isinstance(self.Components[ID], ComponentsModule.WireC) or isinstance(self.Components[ID], ComponentsModule.ComponentPinC)):
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
    Handler = None
    def __init__(self, Component):
        self.StoredAttribute('InitialComponent', Component)
        self.StoredAttribute('Components', set())
        self.StoredAttribute('Connexions', set())
        self.StoredAttribute('Highlightables', set())
        self.StoredAttribute('Level', Params.Board.GroupDefaultLevel)
        self.StoredAttribute('SetBy', None)
        self.AddComponent(Component)
        self.Handler.Groups[self.ID] = self

    @property
    def ID(self):
        return self.InitialComponent.ID

    def Merge(self, Group): 
        for Component in set(Group.Components):
            self.AddComponent(Component)
        if self.IsSet:
            if Group.IsSet:
                self.DualSetWarning(Group.SetBy, 'Merge')
            else:
                self.SetLevel(self.Level, self.SetBy)
        else:
            if Group.IsSet:
                self.SetLevel(Group.Level, Group.SetBy)
            else:
                self.ResetDefaultLevel()
        return Group.ID

    def Split(self, RemovedComponents, Log = False): 
        if not Log:
            def Log(txt):
                pass
        else:
            def Log(txt):
                print(txt)
        self.Highlight(False)
        for Component in RemovedComponents:
            if Component.Group != self:
                raise Exception("Attempting to remove several components from different group at once")
            self.RemoveComponent(Component)
        RemainingComponents = set(self.Components)
        while RemainingComponents:
            ComponentsSet = set()
            StartComponent = RemainingComponents.pop()
            Log(f"Starting with {StartComponent}")
            FoundComponents = {StartComponent}
            while FoundComponents:
                FoundComponent = FoundComponents.pop()
                ComponentsSet.add(FoundComponent)
                Log(f"  Studying {FoundComponent}")
                for ConsideredComponent in FoundComponent.Links:
                    Log(f"      Considering {ConsideredComponent}")
                    if ConsideredComponent in RemainingComponents:
                        FoundComponents.add(ConsideredComponent)
                        RemainingComponents.remove(ConsideredComponent)
                        Log("        Added")
            FoundValidComponent = False
            for Component in ComponentsSet: # We check that at least one component of this group is not a connexion. Groups should not be defined by connexions only
                if not isinstance(Component, ComponentsModule.ConnexionC):
                    FoundValidComponent = True
                    break
            if not self.InitialComponent in ComponentsSet:
                NewGroup = self.__class__(ComponentsSet.pop()) # We take any of the components of this new set as initial component
                for Component in ComponentsSet: # Level setting is taken care of in here
                    NewGroup.AddComponent(Component)
                if NewGroup.SetBy is None: # Incase SetBy existed for self group but was not encountered here, we must ensure that the default level here was implemented 
                    for Component in NewGroup.Components:
                        Component.UpdateStyle()
            else:
                NewGroup = self
            Log(f"Final set for {NewGroup}: {NewGroup.Components}")
            if not FoundValidComponent:
                LogWarning(f"{NewGroup} contains only {len(NewGroup.Connexions)} connexions")

    def AddComponent(self, NewComponent, AutoSet = True):
        Level = None
        if not NewComponent.Group is None:
            if AutoSet and NewComponent.Group.SetBy == NewComponent:
                Level = NewComponent.Group.Level
            NewComponent.Group.RemoveComponent(NewComponent)
        NewComponent.Group = self
        self.Components.add(NewComponent)
        if isinstance(NewComponent, ComponentsModule.ConnexionC):
            self.Connexions.add(NewComponent)
        if not isinstance(NewComponent, ComponentsModule.ConnexionC) and not isinstance(NewComponent, ComponentsModule.ComponentPinC):
            self.Highlightables.add(NewComponent)
        if not Level is None:
            self.SetLevel(Level, NewComponent)

    def RemoveComponent(self, Component, AutoSet = True, AutoRemove = True):
        Component.Group = None
        self.Components.remove(Component)
        self.Connexions.discard(Component)
        self.Highlightables.discard(Component)
        if AutoSet and self.SetBy == Component:
            self.ResetDefaultLevel()
        if not self.Components and AutoRemove:
            del self.Handler.Groups[self.ID]

    def ResetDefaultLevel(self):
        self.SetLevel(Params.Board.GroupDefaultLevel, None)
    def SetLevel(self, Level, Component):
        if not self.SetBy is None and not Component is None and Component != self.SetBy:
            self.DualSetWarning(Component, 'SetLevel')
            return
        self.SetBy = Component
        self.Level = Level
        for Component in self.Components:
            Component.UpdateStyle()
            if Component.TriggersParent:
                self.Handler.UpdateRequest(Component.Parent)

    def DualSetWarning(self, Component, funcStr = ''):
        LogWarning(f"Group {self.ID} set by {Component} and {self.SetBy}" + bool(funcStr)*f" (@{funcStr})")

    @property
    def IsSet(self):
        return not self.SetBy is None

    def Highlight(self, var):
        for Component in self.Highlightables:
            Component.Highlight(var)
    @property
    def Selected(self): # We assume that a group is only selected if the entire group is selected
        for Component in self.Components:
            if not Component.Selected:
                return False
        return True
    @property
    def Removing(self): # We assume that a group is only being removed if the entire group is being removed
        for Component in self.Components:
            if not Component.Removing:
                return False
        return True
    def Fix(self):
        Switched = set()
        for Component in self.Components:
            if type(Component) != ComponentsModule.ComponentPinC:
                Switched.update(Component.Fix())
        return Switched
    def Select(self):
        Switched = set()
        for Component in self.Components:
            if type(Component) != ComponentsModule.ComponentPinC:
                Switched.update(Component.Select())
        return Switched
    def StartRemoving(self):
        Switched = set()
        for Component in self.Components:
            if type(Component) != ComponentsModule.ComponentPinC:
                Switched.update(Component.StartRemoving())
        return Switched
    def Clear(self):
        for Component in self.Components:
            Component.Clear()

    @property
    def Color(self):
        return Colors.Component.Levels[self.Level]
    def __repr__(self):
        return f"Group {self.ID} ({', '.join([Levels.Names[self.Level]]+['unset']*(self.SetBy is None))})"
    def __len__(self): # We do not consider connexions as part of the length of a group
        return len(self.Components.difference(self.Connexions))
    def __contains__(self, Component):
        return Component in self.Components

class CasingGroupC(StorageItem):
    Level = Levels.Undef
    Color = Colors.Component.Levels[Level]
    LibRef = "CGC"
    def __repr__(self):
        return ""
    def AddComponent(self, Component):
        Component.Group = self
    def RemoveComponent(self, Component):
        pass
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
            if isinstance(CompData, type(ComponentsModule.ComponentBase)):
                self.__dict__[CompName] = CompData
                CompData.Book = self
            else:
                self.AddComponentClass(CompName, CompData)
    def __repr__(self):
        return self.Name

    def AddComponentClass(self, CompName, CompData):
        try:
            InputPinsDef, OutputPinsDef, Callback, Schematics, ForceWidth, ForceHeight, DisplayPinNumbering, Symbol = CompData
            PinIDs = set()
            for PinLocation, PinName in InputPinsDef + OutputPinsDef:
                if PinLocation in PinIDs:
                    raise ValueError
        except ValueError:
            LogWarning(f"Unable to load component {Name} from its definition")
            return
        self.__dict__[CompName] = type(CompName, 
                                   (ComponentsModule.CasedComponentC, ), 
                                   {
                                       #'__init__': Components.CasedComponentC.__init__,
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
    ComponentBase = ComponentsModule.ComponentBase # Used to transmit Ax reference
    def __init__(self):
        StorageItem.Library = self

        self.Books = []
        self.Special = {}
        self.AddBook(BookC('Standard', DefaultLibrary.Definitions))
        self.Wire = ComponentsModule.WireC

        self.AddSpecialStorageClass(ComponentsModule.ConnexionC)
        self.AddSpecialStorageClass(ComponentsModule.ComponentPinC)
        self.AddSpecialStorageClass(ComponentsModule.InputPinC)
        self.AddSpecialStorageClass(ComponentsModule.OutputPinC)
        self.AddSpecialStorageClass(GroupC)
        self.AddSpecialStorageClass(CasingGroupC)
        self.AddSpecialStorageClass(ComponentsHandlerC)

        self.AddSpecialStorageClass(ComponentsModule.StatesC)
        for State in ComponentsModule.States.States:
            self.AddSpecialStorageClass(State.__class__)

    def AddBook(self, Book):
        self.__dict__[Book.Name] = Book
        self.Books.append(Book.Name)

    def IsWire(self, C): # Checks if class or class instance
        return C == ComponentsModule.WireC or isinstance(C, ComponentsModule.WireC)
    def IsGroup(self, C):
        return isinstance(C, GroupC)

    def AddSpecialStorageClass(self, Class):
        if '.' in Class.LibRef:
            LogWarning("Special storage class contains forbidden character '.'")
        if Class.LibRef == None:
            LogWarning(f"None LibRef for {Class}")
        self.Special[Class.LibRef] = Class
    def __getitem__(self, LibRef):
        if '.' in LibRef:
            BName, CName = LibRef.split('.')
            return getattr(getattr(self, BName), CName)
        else:
            return self.Special[LibRef]

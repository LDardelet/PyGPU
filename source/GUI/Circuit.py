import numpy as np

import Components as ComponentsModule
from Values import Colors, Params, Levels, PinDict
from Console import Log, LogSuccess, LogWarning, LogError
from Storage import StorageItem, Modifies, BaseLibrary
import DefaultLibrary

class ComponentsHandlerC(StorageItem):
    LibRef = "ComponentsHandler"
    def __init__(self):
        self.StoredAttribute('MaxID', 0)
        self.StoredAttribute('Components', {})
        self.StoredAttribute('Groups', {})
        self.StoredAttribute('Casings', set())
        self.StoredAttribute('Pins', [])
        self.StoredAttribute('InputPins', tuple()) # Tuples for faster looping
        self.StoredAttribute('OutputPins', tuple())
        self.StoredAttribute('CasingGroup', CasingGroupC(self))
        self.StoredAttribute('BoardGroupsHandler', None)

        self.Start()

    def Start(self):
        self.Map = np.zeros((Params.Board.Size, Params.Board.Size, 9), dtype = int)
        for Component in self.Components.values():
            self.RegisterMap(Component)

        self.LiveUpdate = True
        self.Ready = True
        self.AwaitingUpdates = set()

    def Building(func):
        def Wrap(self, *args, **kwargs):
            self.Ready = False
            output = func(self, *args, **kwargs)
            if self.LiveUpdate:
                self.SolveRequests()
            self.Ready = True
            return output
        return Wrap

    def ComputeChain(self):
        Log("Updating chain")

    def CallRequest(self, Component, Backtrace = None):
        if not self.LiveUpdate:
            return
        if Backtrace is None:
            Backtrace = []
        else:
            if Component in Backtrace:
                LogWarning(f"{Component} entered an unstable recursive loop involving {Backtrace}")
                return
        if self.Ready:
            Component(list(Backtrace))
        else:
            self.AwaitingUpdates.add((Component, tuple(Backtrace)))

    def SolveRequests(self):
        while self.AwaitingUpdates:
            Component, Backtrace = self.AwaitingUpdates.pop()
            try:
                Component(list(Backtrace))
            except:
                print("Requests solve error :")
                print(Backtrace)
                print(Component)
                print(Component.Group)
                return

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

        self.CallRequest(NewComponent, Backtrace = ['Register'])    
        return True

    @Modifies
    @Building
    def Remove(self, Components):
        Components = {Component for Component in Components if not isinstance(Component, ComponentsModule.ConnexionC)}
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

    def SetComponent(self, Component): # Sets the ID of a component and stores it, and affects groups before any merge. Handles links through LinkToOthers.
        for Child in Component.Children:
            self.SetComponent(Child)

        self.RegisterMap(Component)
        if not isinstance(Component, ComponentsModule.CasedComponentC):
            GroupC(self, Component)
        else:
            self.CasingGroup.AddComponent(Component)
        self.LinkToOthers(Component)
        if isinstance(Component, ComponentsModule.WireC):
            self.CheckWireMerges(Component)
        if isinstance(Component, ComponentsModule.BoardPinC):
            self.AddBoardPin(Component)

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
            Component = Components.pop()
            Group = Component.Group
            if not Group is None: # Happens if the component was the only one of its group, typically
                GroupComponents = {Component}.union(Components.intersection(Group.Components))
                Components.difference_update(GroupComponents)
                Group.Split(GroupComponents)
            if isinstance(Component, ComponentsModule.BoardPinC):
                self.RemoveBoardPin(Component)
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
            self.Casings.add(Component)
    def Forget(self, Component):
        for Child in Component.Children:
            self.Forget(Child)

        del self.Components[Component.ID]
        if isinstance(Component, ComponentsModule.CasedComponentC):
            self.Casings.remove(Component)

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

    def AddBoardPin(self, Pin):
        Pin.Index = len(self.Pins)
        if Params.GUI.Behaviour.AutoSwitchBoardPins:
            if (Pin.Group.Level == Levels.Undef):
                Pin.Type = PinDict.Input
            else:
                Pin.Type = PinDict.Output
        if Pin.Type == PinDict.Input:
            Pin.Side = PinDict.W
            Pin.TypeIndex = len(self.InputPins)
            Pin.BoardInputSetLevel((self.Input >> Pin.TypeIndex) & 0b1, ['AddBoardPin'])
        else:
            Pin.TypeIndex = len(self.OutputPins)
            Pin.Side = PinDict.E
        self.Pins.append(Pin)
        self.ReloadPinIndices()
        if not self.BoardGroupsHandler is None:
            self.BoardGroupsHandler.Register(Pin)
    def RemoveBoardPin(self, Pin):
        self.Pins.remove(Pin)
        self.ReloadPinIndices()
        if not self.BoardGroupsHandler is None:
            self.BoardGroupsHandler.Unregister(Pin)
    def SetPinIndex(self, Pin, NewIndex, Rule = 'roll'):
        if Pin.Index == NewIndex:
            return
        PreviousIndex = Pin.Index
        if Rule == 'roll':
            self.Pins.remove(Pin)
            self.Pins.insert(NewIndex, Pin)
        elif Rule == 'switch':
            self.Pins[NewIndex], self.Pins[PreviousIndex] = self.Pins[PreviousIndex], self.Pins[NewIndex]
        self.ReloadPinIndices()

    def ReloadPinIndices(self):
        self.InputPins =  tuple([Pin for Pin in self.Pins if Pin.Type == PinDict.Input])
        self.OutputPins = tuple([Pin for Pin in self.Pins if Pin.Type == PinDict.Output])
        for nPin, Pin in enumerate(self.Pins):
            Pin.Index = nPin
        for nPin, Pin in enumerate(self.InputPins):
            Pin.TypeIndex = nPin
        for nPin, Pin in enumerate(self.OutputPins):
            Pin.TypeIndex = nPin

    @property
    def Input(self):
        Input = 0
        for Pin in reversed(self.InputPins): # Use of little-endian norm
            Input = (Input << 1) | (Pin.Level & 0b1)
        return Input
    @Input.setter
    @Modifies
    def Input(self, Input):
        for Pin in self.InputPins:
            Pin.BoardInputSetLevel(Input & 0b1, ['BoardInput'])
            Input = Input >> 1
    @property
    def Output(self):
        Output = 0
        for Pin in reversed(self.OutputPins): # Use of little-endian norm
            Output = (Output << 1) | Pin.Level
        return Output
    @property
    def InputValid(self):
        Valid = 0
        for Pin in reversed(self.InputPins):
            Valid = (Valid << 1) | (Pin.Valid)
        return Valid
    @property
    def OutputValid(self):
        Valid = 0
        for Pin in reversed(self.OutputPins):
            Valid = (Valid << 1) | (Pin.Valid)
        return Valid
    @property
    def NBitsInput(self):
        return len(self.InputPins)
    @property
    def NBitsOutput(self):
        return len(self.InputPins)

    def CheckWireMerges(self, W1):
        for x, y in W1.AdvertisedConnexions:
            Connexion = self.Components[self.Map[x,y,-1]]
            if Connexion.ShouldMergeWires:
                W2 = Connexion.Links.difference({W1}).pop() # Makes merge symetric
                if W1.Group != W2.Group:
                    raise Exception(f"Merging wires {W1} and {W2} from two different groups")
                self.Unlink(W1, Connexion)
                self.Unlink(W2, Connexion)
                for Comp in set(W2.Links):
                    self.Unlink(W2, Comp)
                    self.Link(W1, Comp)
                for x, y, theta in W2.AdvertisedLocations:
                    self.Map[x,y,theta] = W1.ID
                self.Map[x,y,-1] = 0
                W1.Extend(W2)
                W2.destroy()
                Connexion.destroy()
                del self.Components[W2.ID]
                del self.Components[Connexion.ID]

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
        return list({self.Components[ID] for ID in self.Map[Location[0], Location[1],:-1] if (ID and not isinstance(self.Components[ID], ComponentsModule.CasingPinC))})
    def CursorCasings(self, Location):
        return list({Component for Component in self.Casings if Location in Component}) + list({Component for Component in self.Pins if Location in Component})
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
                if not Component.Group in Groups:
                    Groups[Component.Group] = (set(), set())
                if isinstance(Component, ComponentsModule.WireC):
                    Groups[Component.Group][0].add(str(Component.ID))
                else:
                    Groups[Component.Group][1].add(Component)
        if not Groups:
            return ""

        return ', '.join([f'{Group}' + ': '*bool(Group.__repr__()) + ', '.join(bool(Wires)*[f"Wire{'s'*(len(Wires)>1)} ({', '.join(sorted(Wires))})"] + bool(Components)*[', '.join([str(Component) for Component in Components])]) for Group, (Wires, Components) in Groups.items()]) + (len(Groups)>1)*' (isolated)'

    def CasingsInfo(self, Location):
        return ', '.join([str(Casing) for Casing in self.CursorCasings(Location)])

    def FreeSlot(self, Location):
        return (self.Map[Location[0], Location[1], :8] == 0).any()
    def Wired(self, Location):
        for ID in self.Map[Location[0], Location[1], :8]:
            if ID and (isinstance(self.Components[ID], ComponentsModule.WireC) or isinstance(self.Components[ID], ComponentsModule.CasingPinC)):
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
    def __init__(self, Handler, Component):
        self.StoredAttribute('Handler', Handler)
        self.StoredAttribute('InitialComponent', Component)
        self.StoredAttribute('Components', set())
        self.StoredAttribute('Connexions', set())
        self.StoredAttribute('Wires', set())
        self.StoredAttribute('Level', Levels.Undef)
        self.StoredAttribute('SetBy', {})
        self.AddComponent(Component)
        self.Handler.Groups[self.ID] = self

    @property
    def ID(self):
        return self.InitialComponent.ID

    def Merge(self, Group): 
        for Component in set(Group.Components):
            self.AddComponent(Component)

    def CreateGroupFrom(self, ComponentsSet):
        NewGroup = self.__class__(self.Handler, ComponentsSet.pop()) # We take any of the components of this new set as initial component
        for Component in ComponentsSet: # Level setting is taken care of in here
            NewGroup.AddComponent(Component)
        if not NewGroup.SetBy: # Incase SetBy existed for self group but was not encountered here, we must ensure that the default level here was implemented 
            for Component in NewGroup.Components:
                Component.UpdateStyle()
        return NewGroup

    def Split(self, RemovedComponents, Log = False, WarnEmptyGroup = False): 
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
                Group = self.CreateGroupFrom(ComponentsSet)
            else:
                Group = self
            Log(f"Final set for {Group}: {Group.Components}")
            if not FoundValidComponent and WarnEmptyGroup:
                LogWarning(f"{Group} contains only {len(Group.Connexions)} connexions")

    def AddComponent(self, NewComponent, AutoSet = True):
        Level = None
        if not NewComponent.Group is None:
            if AutoSet and NewComponent in NewComponent.Group.SetBy:
                Level = NewComponent.Group.SetBy[NewComponent]
            NewComponent.Group.RemoveComponent(NewComponent)
        else:
            if self.SetBy: # principle check, should never happen, as each new component (.Group is None) is assigned a new Group at first (SetBy == {})
                raise Exception("New component is assigned an existing group at first")
        NewComponent.Group = self
        self.Components.add(NewComponent)
        if isinstance(NewComponent, ComponentsModule.ConnexionC):
            self.Connexions.add(NewComponent)
        if isinstance(NewComponent, ComponentsModule.WireC):
            self.Wires.add(NewComponent)
        if not Level is None:
            self.SetLevel(Level, NewComponent, ['AddGroupComponent'])
        else:
            self.TriggerComponentLevel(NewComponent, ['AddGroupComponent'])

    def RemoveComponent(self, Component, AutoSet = True, AutoRemove = True):
        Component.Group = None
        self.Components.remove(Component)
        self.Connexions.discard(Component)
        self.Wires.discard(Component)
        if AutoSet and (Component in self.SetBy):
            self.RemoveLevelSet(Component)
        if not self.Components and AutoRemove:
            del self.Handler.Groups[self.ID]

    def SetLevel(self, Level, Component, Backtrace, Log = False, Warn = True):
        if Log:
            if not Level is None:
                print(self, self.Level, 'set to', Levels.Names[Level], 'by', Component)
            else:
                print(self, self.Level, "to default set")
        if Component != None:
            self.SetBy[Component] = Level
        PrevLevel = self.Level
        if len(self.SetBy) == 1:
            self.Level = Level
        elif len(self.SetBy) == 0:
            if Warn and self.StillUseful:
                self.UnsetWarning()
            self.Level = Levels.Undef
        else:
            if Warn:
                self.MultipleSetWarning()
            self.Level = Levels.Multiple
        if PrevLevel != self.Level:
            for Component in self.Components:
                self.TriggerComponentLevel(Component, Backtrace)
        else:
            if not Component is None:
                self.TriggerComponentLevel(Component, Backtrace)
    def RemoveLevelSet(self, Component):
        if not Component in self.SetBy:
            raise Exception("{Component} was not level setter for {self}")
        del self.SetBy[Component]
        if not self.SetBy:
            self.SetLevel(None, None, [f'RemoveGroupComponent(1) {self}'], Warn = False)
        else:
            PickedComponent = list(self.SetBy.keys())[0]
            self.SetLevel(self.SetBy[PickedComponent], PickedComponent, [f'RemoveGroupComponent(2) {self}'], Warn = False)

    def TriggerComponentLevel(self, Component, Backtrace):
        Component.UpdateStyle()
        if Component.TriggersParent:
            self.Handler.CallRequest(Component.Parent, Backtrace)
    def UnsetWarning(self):
        LogWarning(f"Group {self.ID} not set anymore")
    def MultipleSetWarning(self):
        LogWarning(f"Group {self.ID} set by {', '.join([str(Component) for Component in self.SetBy])}")

    def Highlight(self, var):
        for Wire in self.Wires:
            Wire.Highlight(var)
    @property
    def Selected(self): # We assume that a group is only selected if the entire group is selected
        for Wire in self.Wires:
            if not Wire.Selected:
                return False
        return True
    @property
    def Removing(self): # We assume that a group is only being removed if the entire group is being removed
        for Wire in self.Wires:
            if not Wire.Removing:
                return False
        return True
    def Fix(self):
        Switched = set()
        for Component in self.Components:
            if type(Component) != ComponentsModule.CasingPinC:
                Switched.update(Component.Fix())
        return Switched
    def Select(self):
        Switched = set()
        for Wire in self.Wires:
            Switched.update(Wire.Select())
        return Switched
    def StartRemoving(self):
        Switched = set()
        for Wire in self.Wires:
            Switched.update(Wire.StartRemoving())
        return Switched
    def Clear(self):
        for Component in self.Components:
            Component.Clear()
    def Switch(self):
        pass

    @property
    def Color(self):
        return Colors.Component.Levels[self.Level]
    def __repr__(self):
        return f"Group {self.ID}"
    @property
    def StillUseful(self):
        return len(self.Components) > len(self.Connexions)
    def __len__(self): # We do not consider connexions as part of the length of a group
        return len(self.Components) - len(self.Connexions)
    def __contains__(self, Component):
        return Component in self.Components

class CasingGroupC(StorageItem):
    Level = Levels.Undef
    Color = Colors.Component.Levels[Level]
    LibRef = "CGC"
    def __init__(self, Handler):
        self.StoredAttribute("Handler", Handler)
        self.StoredAttribute("Components", set())
    def __repr__(self):
        return "Casings"
    def AddComponent(self, Component):
        Component.Group = self
        self.Components.add(Component)
    def RemoveComponent(self, Component):
        self.Components.remove(Component)
    def Split(self, Components):
        for Component in Components:
            self.RemoveComponent(Component)

# Component template signature :
# (InputPins, OutputPins, Callback, Board, ForceWidth, ForceHeight, PinLabelRule, Symbol)

class BookC:
    def __init__(self, Name, BookComponents = {}):
        self.Name = Name
        self.Components = []
        for CompName, (CompData, ControlKey) in BookComponents.items():
            if hasattr(self, CompName):
                LogWarning(f"Component name {CompName} already exists in this book")
                continue
            self.Components.append(CompName)
            if isinstance(CompData, type(ComponentsModule.ComponentBase)):
                CompClass = CompData
                CompClass.Book = self
            else:
                CompClass = self.CreateComponentClass(CompName, CompData)
                if CompClass is None:
                    continue
            setattr(self, CompName, CompClass)
            setattr(self, 'key_'+CompName, ControlKey)
    def __repr__(self):
        return self.Name

    def CreateComponentClass(self, CompName, CompData):
        try:
            InputPinsDef, OutputPinsDef, Callback, UndefRun, Board, ForceWidth, ForceHeight, PinLabelRule, Symbol = CompData
            PinIDs = set()
            for PinLocation, PinName in InputPinsDef + OutputPinsDef:
                if PinLocation in PinIDs:
                    raise ValueError
        except ValueError:
            LogWarning(f"Unable to load component {CompName} from its definition")
            return
        return type(CompName, 
                    (ComponentsModule.CasedComponentC, ), 
                    {
                        #'__init__': Components.CasedComponentC.__init__,
                        'CName': CompName,
                        'Book': self.Name,
                        'InputPinsDef'    : InputPinsDef,
                        'OutputPinsDef'    : OutputPinsDef,
                        'Callback'   : Callback,
                        'UndefRun'   : UndefRun,
                        'Board' : Board,
                        'ForceWidth' : ForceWidth,
                        'ForceHeight': ForceHeight,
                        'PinLabelRule':PinLabelRule,
                        'Symbol':Symbol,
                    })

class CLibrary:
    ComponentBase = ComponentsModule.ComponentBase # Used to transmit Ax reference
    def __init__(self):
        StorageItem.GeneralLibrary = self

        self.Books = []
        self.Special = {}
        self.AddBook(BookC('Standard', DefaultLibrary.Definitions))
        self.Wire = ComponentsModule.WireC

    def AddBook(self, Book):
        setattr(self, Book.Name, Book)
        self.Books.append(Book.Name)

    def IsWire(self, C): # Checks if class or class instance
        return C == ComponentsModule.WireC or isinstance(C, ComponentsModule.WireC)
    def IsBoardPin(self, C): # Checks if class or class instance
        return C == ComponentsModule.BoardPinC or isinstance(C, ComponentsModule.BoardPinC)
    def IsGroup(self, C):
        return isinstance(C, GroupC)

    def __getitem__(self, LibRef):
        if '.' in LibRef:
            BName, CName = LibRef.split('.')
            return getattr(getattr(self, BName), CName)
        else:
            return self.Special[LibRef]

BaseLibrary.Advertise(GroupC)
BaseLibrary.Advertise(CasingGroupC)
BaseLibrary.Advertise(ComponentsHandlerC)

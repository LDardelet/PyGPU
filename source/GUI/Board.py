import numpy as np

from Circuit import ComponentsHandlerC
from Storage import FileSavedEntityC, StorageItem

from Values import PinDict
from Console import Log, LogWarning, LogSuccess

class TruthTableC(StorageItem):
    LibRef = "TruthTable"
    def __init__(self):
        self.StoredAttribute('Data', np.zeros(0, dtype = int))
        self.StoredAttribute('UpToDate', False)

class BoardGroupsHandlerC(StorageItem):
    LibRef = "BoardGroupsHandlerC"
    NoneBoardGroupID = (PinDict.NoneBoardGroupName, None)
    def __init__(self):
        self.StoredAttribute('Groups', {self.NoneBoardGroupID:set()})
        self.StoredAttribute('Pins', {})
    def Register(self, Pin):
        Pin.BoardGroup = self
        self.Groups[self.NoneBoardGroupID].add(Pin)
        self.Pins[Pin] = self.NoneBoardGroupID
    def Unregister(self, Pin):
        self.Groups[self.Pins[Pin]].remove(Pin)
        del self.Pins[Pin]
        Pin.BoardGroup = None
    def Set(self, Pin, GroupName = None):
        if GroupName != PinDict.NoneBoardGroupName and GroupName not in PinDict.BoardGroupsNames[Pin.Type]:
            raise Exception("Wrong board group for pin {Pin}")
        InitialGroupName = self.Pins[Pin]
        self.Groups[InitialGroupName].remove(Pin)
        if InitialGroupName != self.NoneBoardGroupID and not self.Groups[InitialGroupName]:
            del self.Groups[InitialGroupName]

        GroupID = (GroupName, Pin.Type)
        if GroupID not in self.Groups:
            self.Groups[GroupID] = {Pin}
        else:
            self.Groups[GroupID].add(Pin)
        self.Pins[Pin] = GroupID
    def Index(self, Pin):
        return sorted(reversed([GroupPin.Index for GroupPin in self.Groups[self.Pins[Pin]]])).index(Pin.Index) # Reverse for little endian
    @property
    def InputGroups(self):
        return {(GroupName, GroupType):Pins for (GroupName, GroupType), Pins in self.Groups.items() if GroupType == PinDict.Input}
    @property
    def OutputGroups(self):
        return {(GroupName, GroupType):Pins for (GroupName, GroupType), Pins in self.Groups.items() if GroupType == PinDict.Output}
    def __call__(self, Pin):
        return self.Pins[Pin][0]
    def Name(self, Pin):
        if self.Pins[Pin] == self.NoneBoardGroupID:
            return ''
        return f"{self.Pins[Pin][0]}{self.Index(Pin)}"

class BoardC(FileSavedEntityC):
    LibRef = "BoardC"
    Untitled = "Untitled"
    Display = None
    def __init__(self, Filename = None, Display = None, ParentBoard = None):
        self.StoredAttribute('ComponentsHandler', ComponentsHandlerC())
        self.StoredAttribute('TruthTable', TruthTableC())
        self.StoredAttribute('BoardGroupsHandler', BoardGroupsHandlerC())
        self.StoredAttribute('Name', '')

        self.Filename = Filename

        self.ParentBoard = ParentBoard
        self.LoadedBoards = []

        self._LiveUpdate = True

        self.Display = Display
        self.Display.Board = self
        if self.Filed:
            FileSavedEntityC.Load(self)
        
        self.ComponentsHandler.BoardGroupsHandler = self.BoardGroupsHandler
        self.Display.SetView()

    @property
    def Displayed(self):
        return self.Display is None

    def Save(self, Filename, Force = False):
        if self.Saved and not Force:
            return True
        if not self.ParentBoard is None:
            LogWarning("Cannot save a board opened as a component")
            return False
        self.Filename = Filename
        self.Name = Filename.split('/')[-1].split('.')[0]

        return FileSavedEntityC.Save(self)

    def Run(self, Input):
        if self.TruthTable.UpToDate and not self.Displayed:
            return self.TruthTable.Evaluate(Input)
        else:
            self.Input = Input
            self.ComponentsHandler.SolveRequests()
            return self.Output

    def ComputeTruthTable(self):
        StoredInput = self.Input

        N = 2**self.NBitsInput
        Data = np.zeros(N, dtype = int)
        self.ComponentsHandler.Ready = False
        for Input in range(N):
            self.Input = Input
            self.ComponentsHandler.SolveRequests()
            Data[Input] = self.Output
        self.TruthTable.Data = Data
        self.TruthTable.UpToDate = True
        Log("Done!")
        self.Input = StoredInput
        self.ComponentsHandler.SolveRequests()
        self.ComponentsHandler.Ready = True

    @property
    def Filed(self):
        return not self.Filename is None

    @property
    def Saved(self):
        return self.ComponentsHandler._Saved

    @property
    def LiveUpdate(self):
        return self._LiveUpdate
    @LiveUpdate.setter
    def LiveUpdate(self, value):
        self._LiveUpdate = value
        if self._LiveUpdate:
            self.ComponentsHandler.SolveRequests()
    def Building(func):
        def WrapBuild(self, *args, **kwargs):
            self.ComponentsHandler.Ready = False
            self.ComponentsHandler._Saved = False
            self.TruthTable.UpToDate = False
            output = func(self, *args, **kwargs)
            if self.LiveUpdate:
                self.ComponentsHandler.SolveRequests()
            self.ComponentsHandler.Ready = True
            return output
        return WrapBuild

    @property
    def NBitsInput(self):
        return len(self.ComponentsHandler.InputPins)
    @property
    def NBitsOutput(self):
        return len(self.ComponentsHandler.OutputPins)
    @property
    def Pins(self):
        return self.ComponentsHandler.Pins
    @property
    def InputPins(self):
        return self.ComponentsHandler.InputPins
    @property
    def OutputPins(self):
        return self.ComponentsHandler.OutputPins
    @property
    def Groups(self):
        return self.BoardGroupsHandler.Groups
    @property
    def InputGroups(self):
        return self.BoardGroupsHandler.InputGroups
    @property
    def OutputGroups(self):
        return self.BoardGroupsHandler.OutputGroups
    @property
    def Input(self):
        Input = 0
        for Pin in reversed(self.ComponentsHandler.InputPins): # Use of little-endian norm
            Input = (Input << 1) | (Pin.Level & 0b1)
        return Input
    @Input.setter
    def Input(self, Input):
        self.ComponentsHandler._Saved = False
        for Pin in self.ComponentsHandler.InputPins:
            Pin.BoardInputSetLevel(Input & 0b1, ['BoardInput'])
            Input = Input >> 1
    @property
    def Output(self):
        Output = 0
        for Pin in reversed(self.ComponentsHandler.OutputPins): # Use of little-endian norm
            Output = (Output << 1) | (Pin.Level & 0b1)
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

    # Transfered public ComponentsHandler methods:
    @Building
    def Register(self, *args, **kwargs):
        return self.ComponentsHandler.Register(*args, **kwargs)
    @Building
    def Remove(self, *args, **kwargs):
        return self.ComponentsHandler.Remove(*args, **kwargs)
    @Building
    def ToggleConnexion(self, *args, **kwargs):
        return self.ComponentsHandler.ToggleConnexion(*args, **kwargs)
    def SetPinIndex(self, *args, **kwargs):
        return self.ComponentsHandler.SetPinIndex(*args, **kwargs)
    def HasItem(self, *args, **kwargs):
        return self.ComponentsHandler.HasItem(*args, **kwargs)
    def FreeSlot(self, *args, **kwargs):
        return self.ComponentsHandler.FreeSlot(*args, **kwargs)
    def GroupsInfo(self, *args, **kwargs):
        return self.ComponentsHandler.GroupsInfo(*args, **kwargs)
    def CursorGroups(self, *args, **kwargs):
        return self.ComponentsHandler.CursorGroups(*args, **kwargs)
    def CursorComponents(self, *args, **kwargs):
        return self.ComponentsHandler.CursorComponents(*args, **kwargs)
    def CursorCasings(self, *args, **kwargs):
        return self.ComponentsHandler.CursorCasings(*args, **kwargs)
    def CursorConnected(self, *args, **kwargs):
        return self.ComponentsHandler.CursorConnected(*args, **kwargs)
    def CanToggleConnexion(self, *args, **kwargs):
        return self.ComponentsHandler.CanToggleConnexion(*args, **kwargs)
    

    def __repr__(self):
        if self.Filed:
            return self.Name
        else:
            return self.Untitled

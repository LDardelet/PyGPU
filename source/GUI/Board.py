import numpy as np

from Circuit import ComponentsHandlerC
from Storage import FileHandlerC, StorageItem, BaseLibrary

from Values import PinDict
from Console import Log, LogWarning, LogSuccess

class TruthTableC(StorageItem):
    LibRef = "TruthTable"
    def __init__(self):
        self.StoredAttribute('Data', np.zeros(0, dtype = int))
        self.UpToDate = False

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

class BoardC:
    Untitled = "Untitled"
    _SavedItems = (('ComponentsHandler', ComponentsHandlerC),
                  ('TruthTable', TruthTableC),
                  ('BoardGroupsHandler', BoardGroupsHandlerC))
    def __init__(self, Filename = None, Display = None, ParentBoard = None):
        self.FileHandler = FileHandlerC()
        self.Filename = Filename

        self.ParentBoard = ParentBoard
        self.LoadedBoards = []

        self.Display = Display
        self.Display.Board = self
        if self.Filed:
            self.FileHandler.Load(self.Filename)
            for Item, _ in self._SavedItems:
                setattr(self, Item, self.FileHandler[Item])
        else:
            for Item, DefaultClass in self._SavedItems:
                setattr(self, Item, DefaultClass())
        
        self.ComponentsHandler.BoardGroupsHandler = self.BoardGroupsHandler
        self.Display.SetView()

    def Save(self, Filename, Force = False):
        if self.Saved and not Force:
            return True
        if not self.ParentBoard is None:
            LogWarning("Cannot save a board opened as a component")
            return False
        self.Filename = Filename
        self.FileHandler.Save(Filename, **{Item: getattr(self, Item) for Item, _ in self._SavedItems})
        return True

    def ComputeTruthTable(self):
        StoredInput = self.ComponentsHandler.Input

        N = 2**self.ComponentsHandler.NBitsInput
        Data = np.zeros(N, dtype = int)
        self.ComponentsHandler.Ready = False
        for Input in range(N):
            self.ComponentsHandler.Input = Input
            self.ComponentsHandler.SolveRequests()
            Data[Input] = self.ComponentsHandler.Output
        self.TruthTable.Data = Data
        Log("Done!")
        self.ComponentsHandler.Input = StoredInput
        self.ComponentsHandler.SolveRequests()
        self.ComponentsHandler.Ready = True

    @property
    def Name(self):
        if self.Filed:
            BoardName = self.Filename.split('/')[-1]
        else:
            BoardName = self.Untitled
        return BoardName

    @property
    def Filed(self):
        return not self.Filename is None

    @property
    def Saved(self):
        return self.ComponentsHandler._Saved

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

BaseLibrary.Advertise(TruthTableC)
BaseLibrary.Advertise(BoardGroupsHandlerC)

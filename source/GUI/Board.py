import numpy as np

from Circuit import ComponentsHandlerC, TruthTableC
from Storage import FileHandlerC

from Values import PinDict, BoardGroupsDict
from Console import Log, LogWarning, LogSuccess

class BoardC:
    Untitled = "Untitled"
    _SavedItems = (('ComponentsHandler', ComponentsHandlerC),
                  ('TruthTable', TruthTableC))
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
        Pins = {GroupName:set() for GroupName in ('',) + BoardGroupsDict.Names[PinDict.Input] + BoardGroupsDict.Names[PinDict.Output]}
        for Pin in self.Pins:
            Pins[Pin.BoardGroup].add(Pin.TypeIndex)
        Groups = {}
        for GroupType in (PinDict.Input, PinDict.Output):
            Index = 0
            for GroupName in BoardGroupsDict.Names[GroupType]:
                if Pins[GroupName]:
                    Groups[(GroupName, GroupType)] = (Index, tuple(Pins[GroupName]))
                    Index += 1
        return Groups
    @property
    def InputGroups(self):
        Pins = {GroupName:set() for GroupName in ('',) + BoardGroupsDict.Names[PinDict.Input]}
        for Pin in self.InputPins:
            Pins[Pin.BoardGroup].add(Pin.TypeIndex)
        Index = 0
        Groups = {}
        for GroupName in BoardGroupsDict.Names[PinDict.Input]:
            if Pins[GroupName]:
                Groups[(GroupName, PinDict.Input)] = (Index, tuple(Pins[GroupName]))
                Index += 1
        return Groups
    @property
    def OutputGroups(self):
        Pins = {GroupName:set() for GroupName in ('',) + BoardGroupsDict.Names[PinDict.Output]}
        for Pin in self.OutputPins:
            Pins[Pin.BoardGroup].add(Pin.TypeIndex)
        Index = 0
        Groups = {}
        for GroupName in BoardGroupsDict.Names[PinDict.Output]:
            if Pins[GroupName]:
                Groups[(GroupName, PinDict.Output)] = (Index, tuple(Pins[GroupName]))
                Index += 1
        return Groups


class BoardGroup:
    def __init__(self, Name, Pins, Type):
        self.Name = Name
        self.Pins = Pins
        self.Type = Type

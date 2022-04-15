import tkinter as Tk
from tkinter import ttk
from tkinter import messagebox
from PIL import Image
import os, sys
import sys
import numpy as np

import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from Console import ConsoleWidget, ConsoleText, Log, LogSuccess, LogWarning, LogError
from Values import Colors, Params, PinDict
from Tools import Void, ModesDict, ModeC, SFrame, SEntry, SLabel, SPinEntry, BoardIOWidgetBase, BoardDisplayC
from Circuit import CLibrary
from Board import BoardC
from Export import ExportGUI

matplotlib.use("TkAgg")

class GUI:
    Modes = ModesDict() # Here as we need mode decorator
    NewBoardStr = "New board"
    def Trigger(func):
        def WrapTrigger(self, *args, **kwargs):
            UpdateWhenFinished = False
            if not self.UpdateLocked:
                self.UpdateLocked = True
                UpdateWhenFinished = True
            res = func(self, *args, **kwargs)
            if UpdateWhenFinished:
                self.SolveUpdateRequests(func)
            return res
        return WrapTrigger
    def Update(*UpdateFunctions):
        def Wrapper(func):
            def WrapUpdate(self, *args, **kwargs):
                for UpdateFunction in UpdateFunctions:
                    UpdateFunction.Callers.add(func.__name__)
                return func(self, *args, **kwargs)
            return WrapUpdate
        return Wrapper

    def LocalView(self):
        self.CurrentDisplay.Canvas.draw()
    def BoardState(self):
        for BoardInputWidget in self.BoardInputWidgets:
            BoardInputWidget.Pull(self.CH.Input, self.CH.InputValid)
        if self.CH.LiveUpdate:
            for BoardOutputWidget in self.BoardOutputWidgets:
                BoardOutputWidget.Pull(self.CH.Output, self.CH.OutputValid)
        self.CurrentDisplay.Canvas.draw()
    def CursorInfo(self):
        GroupsInfo = self.CH.GroupsInfo(self.Cursor)
        self.MainFrame.Board.DisplayToolbar.Labels.CursorLabel['text'] = f"{self.Cursor.tolist()}" + bool(GroupsInfo)*": " + self.CH.GroupsInfo(self.Cursor)
        if self.Highlighted is None:
            Info = ""
        else:
            Info = str(self.Highlighted)
        self.MainFrame.Board.DisplayToolbar.Labels.HighlightLabel['text'] = f"Highlight: {Info}"
    def BoardPinsLayout(self):
        InputGroups = self.CurrentBoard.InputGroups
        OutputGroups = self.CurrentBoard.OutputGroups

        def Row(Pin):
            if Pin.Type == PinDict.Input:
                return 1+len(InputGroups)+Pin.TypeIndex
            else:
                return 1+len(OutputGroups)+Pin.TypeIndex

        for Pin, PinEntry in list(self.DisplayedPinsWidgets.items()):
            if Pin not in self.CurrentBoard.Pins or PinEntry.Type != Pin.Type:
                if Pin.Type == PinDict.Input:
                    WidgetParentFrame = self.MainFrame.Right_Panel.Input_Pins
                    BoardWidgetSet = self.BoardInputWidgets
                else:
                    WidgetParentFrame = self.MainFrame.Right_Panel.Output_Pins
                    BoardWidgetSet = self.BoardOutputWidgets
                PinWidget = self.DisplayedPinsWidgets[Pin]
                WidgetParentFrame.Destroy(f"PinFrame{Pin.ID}")
                BoardWidgetSet.remove(PinWidget)
                del self.DisplayedPinsWidgets[Pin]
            else: # We ensure the pin is in the right location
                PinEntry.Bits = (Pin.TypeIndex, )
                PinEntry.frame.grid(row = Row(Pin), column = 0)
                PinEntry.UpdateNameInGroup()
        for Pin in self.CurrentBoard.Pins:
            if Pin not in self.DisplayedPinsWidgets:
                if Pin.Type == PinDict.Input:
                    WidgetParentFrame = self.MainFrame.Right_Panel.Input_Pins
                    BoardWidgetSet = self.BoardInputWidgets
                else:
                    WidgetParentFrame = self.MainFrame.Right_Panel.Output_Pins
                    BoardWidgetSet = self.BoardOutputWidgets
                PinFrame = WidgetParentFrame.AddFrame(f"PinFrame{Pin.ID}", row = Row(Pin), column = 0, Border = True, NoName = True)
                PinEntry = SPinEntry(PinFrame, Pin)
                self.DisplayedPinsWidgets[Pin] = PinEntry
                BoardWidgetSet.add(PinEntry)
        
        for GroupType, UsedGroups, WidgetParentFrame, BoardWidgetSet, SWidget in ((PinDict.Input,  InputGroups,  self.MainFrame.Right_Panel.Input_Groups,  self.BoardInputWidgets,  SEntry),
                                                                          (PinDict.Output, OutputGroups, self.MainFrame.Right_Panel.Output_Groups, self.BoardOutputWidgets, SLabel)):
            for GroupName in PinDict.BoardGroupsNames[GroupType]:
                GroupID = (GroupName, GroupType)
                GroupFrameName = f"GroupFrame{GroupName}"
                if GroupID in UsedGroups:
                    GroupBits = tuple(sorted([Pin.TypeIndex for Pin in UsedGroups[GroupID]]))
                    GroupRow = 1+[PossibleGroupName for PossibleGroupName in PinDict.BoardGroupsNames[GroupType] if (PossibleGroupName, GroupType) in UsedGroups].index(GroupName)
                    if GroupID in self.DisplayedGroupsWidgets:
                        GroupWidget = self.DisplayedGroupsWidgets[GroupID]
                        GroupWidget.Bits = GroupBits
                        GroupWidget.frame.grid(row = GroupRow, column = 0)
                    else:
                        GroupFrame = WidgetParentFrame.AddFrame(GroupFrameName, row = GroupRow, column = 0, Border = True, NoName = True)
                        GroupWidget = SWidget(GroupFrame, GroupName, GroupBits, Params.GUI.RightPanel.Width//2, True)
                        BoardWidgetSet.add(GroupWidget)
                        self.DisplayedGroupsWidgets[GroupID] = GroupWidget
                else:
                    if GroupID in self.DisplayedGroupsWidgets:
                        GroupWidget = self.DisplayedGroupsWidgets[GroupID]
                        WidgetParentFrame.Destroy(GroupFrameName)
                        BoardWidgetSet.remove(GroupWidget)
                        del self.DisplayedGroupsWidgets[GroupID]

        self.BoardInputEntry.Bits = tuple(range(len(self.CurrentBoard.InputPins)))
        self.BoardOutputLabel.Bits = tuple(range(len(self.CurrentBoard.OutputPins)))
    def BoardsList(self):
        self.BoardsMenu['menu'].delete(0, "end")
        Boards = []
        FoundBoards = set()

        def UnpackBoards(Current, Tab = 0, Prefix = '', UnfiledID = 1):
            for Board in Current.LoadedBoards:
                if Board in FoundBoards:
                    continue

                BoardName = Board.Name
                if not Board.Filed:
                    BoardName = Board.Name + f'({UnfiledID})'
                    UnfiledID += 1
                Name = Tab*' ' + Prefix + BoardName

                Boards.append((Name, Board))
                FoundBoards.add(Board)
                UnpackBoards(Board, Tab + 2, '->')
        UnpackBoards(self)

        for BoardName, Board in Boards+[(self.NewBoardStr, None)]:
            self.BoardsMenu['menu'].add_command(label=BoardName, command = lambda *args, Board = Board, self=self, **kwargs:self.MenuSelectBoardName(Board))
            if Board == self.CurrentBoard:
                self.BoardVar.set(BoardName)

    def SolveUpdateRequests(self, func, Log = True):
        if Log:
            print(f"Triggered by {func.__name__}")
        for UpdateFunction in self.UpdateFunctions:
            if UpdateFunction.Callers:
                if Log:
                    print(f"  * {UpdateFunction.__name__} called by {UpdateFunction.Callers}")
                UpdateFunction(self)
                UpdateFunction.Callers.clear()
        self.UpdateLocked = False

    UpdateFunctions = (BoardsList, BoardPinsLayout, CursorInfo, BoardState, LocalView)
    for UpdateFunction in UpdateFunctions:
        UpdateFunction.Callers = set()
    UpdateLocked = False

    def __init__(self, Args):
        if not os.path.exists(Params.GUI.DataAbsPath):
            os.mkdir(Params.GUI.DataAbsPath)
        for DataSubFolder in Params.GUI.DataSubFolders:
            if not os.path.exists(Params.GUI.DataAbsPath + DataSubFolder):
                os.mkdir(Params.GUI.DataAbsPath + DataSubFolder)

        self.MainWindow = Tk.Tk()

        BoardIOWidgetBase.GUI = self
        ModeC.GUI = self
        self.Library = CLibrary()
        self.LoadedBoards = []
        self.LoadedDisplays = []
        self.CurrentBoard = None
        self.CurrentDisplay = None
        self.DisplayedPinsWidgets = {}
        self.DisplayedGroupsWidgets = {}

        self.LoadGUI()

        self.ResetBoardGUIVariables()
        if len(Args) > 1:
            self.Open(New=False, Filename=Args[1])
        else:
            self.Open(New=True)

        self.SolveUpdateRequests(self.__init__)

        self.MainWindow.mainloop()

    @Trigger
    def OnClickMove(self, Click):
        if self.Modes.Text:
            self.Modes.Default(Message='Click')
        self.Cursor = np.rint(Click).astype(int)
        self.OnMove()

    @Trigger
    def BoardIOWidgetReturnCallback(self, Entry):
        self.Modes.Default(Message = f'Entry return by {Entry}')

    @Trigger
    @Update(BoardPinsLayout, BoardState)
    def BoardIOWidgetGroupModification(self):
        pass

    @Trigger
    @Update(BoardState)
    def BoardIOWidgetLevelModificationCallback(self, Entry): # TODO : seems to be missing a trigger, to update the GUI widgets layout upon board grouop change
        self.CH.Input = Entry.Push(self.CH.Input)

    @Trigger  # TODO : merge all callback functions to OnUserAction
    def OnStaticGUIButton(self, Callback, *args, **kwargs):
        return Callback(*args, **kwargs)

    @Trigger
    def OnKeyRegistration(self, Callback, Key, Mod):
        Callback(Key, Mod)

    @Trigger
    def OnComponentButtonClick(self, ComponentClass):
        self.StartComponent(ComponentClass)

    @Trigger
    def MenuSelectBoardName(self, Board):
        if Board is None:
            self.Open(New=True)
        else:
            if Board == self.CurrentBoard:
                return
            print(f"Selected {Board.Name}")
            self.SelectBoard(Board)

    # Update functions. No trigger should be within here, apart from simulation run

    def ResetBoardGUIVariables(self):
        self.Rotation = 0
        self.CanHighlight = [None]
        self.Highlighted = None
        self.TmpComponents = set()

    def ClearBoard(self):
        self.CH.LiveUpdate = False # Possibly useless
        self.CurrentDisplay.Ax.cla()
        self.PlotView()
        return True

    @Update(BoardsList)
    @Modes.Default
    def SaveBoard(self, SelectFilename = False):
        if self.CurrentBoard.Filename is None or SelectFilename:
            Filename = Tk.filedialog.asksaveasfilename(initialdir = os.path.abspath(Params.GUI.DataAbsPath + Params.GUI.DataSubFolders['Projects']), filetypes=[('BOARD file', '.brd')], defaultextension = '.brd')
            Force = True
        else:
            Filename = self.CurrentBoard.Filename
            Force = False
        if Filename:
            Success = self.CurrentBoard.Save(Filename, Force = Force)
            if Success:
                self.MainWindow.title(Params.GUI.Name + f" ({self.CurrentBoard.Name})")
            return Success
        else:
            LogWarning("Data unsaved")

    @Modes.Default
    def ExportBoardAsComponent(self):
        if False and len(self.CH.InputPins) == 0 and len(self.CH.OutputPins) == 0:
            Log("Impossible to export a board without any IO pin")
            return

        Export = ExportGUI(self.MainWindow, self.CurrentBoard)
        Export.MainWindow.wait_window()
        if Export.Success:
            Log("Success")
        else:
            LogWarning("Component export failed")

    def Open(self, New=False, Filename=''):
        if New:
            Log("Starting new board")
            self.LoadedBoards.append(BoardC(None, self.NewDisplay()))
        else:
            if not Filename:
                Filename = Tk.filedialog.askopenfilename(initialdir = os.path.abspath(Params.GUI.DataAbsPath + Params.GUI.DataSubFolders['Projects']), filetypes=[('BOARD file', '.brd')], defaultextension = '.brd')
            if Filename:
                for Board in self.LoadedBoards:
                    if Board.Filename == Filename:
                        Log("Board already opened")
                        self.SelectBoard(Board)
                        return
                LoadingDisplay = self.NewDisplay()
                self.Library.ComponentBase.Display = LoadingDisplay.Ax
                self.LoadedBoards.append(BoardC(Filename, LoadingDisplay))
            else:
                return
        self.SelectBoard(self.LoadedBoards[-1])

    @Update(BoardsList)
    def CloseBoard(self, Board = None):
        if Board is None:
            Board = self.CurrentBoard
        if not Board.Saved:
            ans = messagebox.askyesnocancel("Unsaved changes", f"Save changes to board {Board.Name} before closing?")
            if ans is None:
                return
            if ans:
                if not self.SaveBoard():
                    return
        Index = self.LoadedBoards.index(Board)
        self.LoadedBoards.remove(Board)
        if not Board.Display is None:
            self.LoadedDisplays.remove(Board.Display)
        if len(self.LoadedBoards) == 0:
            self.MenuSelectBoardName(None)
        else:
            self.SelectBoard(self.LoadedBoards[max(0, Index-1)])

    @Update(BoardsList, BoardPinsLayout, BoardState)
    @Modes.Default
    def SelectBoard(self, Board):
        if not self.CurrentBoard is None:
            self.ClearTmpComponents()

        self.CurrentBoard = Board
        self.SelectDisplay(Board.Display)

        self.ResetBoardGUIVariables()

        self.MainWindow.title(Params.GUI.Name + f" ({self.CurrentBoard.Name})")

    @property
    def Cursor(self):
        return self.CurrentDisplay.Cursor
    @Cursor.setter
    def Cursor(self, value):
        self.CurrentDisplay.Cursor = value
    @property
    def CH(self):
        return self.CurrentBoard.ComponentsHandler

    @Update(LocalView)
    def SelectDisplay(self, Display):
        if not self.CurrentDisplay is None:
            self.CurrentDisplay.Widget.grid_forget()
        self.CurrentDisplay = Display
        self.CurrentDisplay.Widget.grid(row = 0, column = 0)

        self.UpdateCursorStyle() # Display is loaded with a default black color to reduce Tools interactions with modes. Need to update it right away
        self.Library.ComponentBase.Display = self.CurrentDisplay.Ax

        self.CurrentDisplay.Canvas.mpl_connect('button_press_event', lambda e:self.OnClickMove(np.array([e.xdata, e.ydata])))
        self.MainWidget = self.CurrentDisplay.Widget
        self.MainWidget.bind('<FocusOut>', lambda e:self.CheckFocusOut())
        self.MainWidget.focus_set()

    def NewDisplay(self):
        NewDisplay = BoardDisplayC()
        self.LoadedDisplays.append(NewDisplay)
        NewDisplay.SetView()

        return NewDisplay

    @Modes.Build
    @Update(LocalView)
    def StartComponent(self, CClass, Rotation = 0, Symmetric = False):
        self.SetLibraryButtonColor(self.CompToButtonMap[CClass])
        self.TmpComponents.add(CClass(self.Cursor, Rotation, Symmetric))

    @Update(LocalView)
    def ClearTmpComponents(self):
        while self.TmpComponents:
            self.TmpComponents.pop().Clear()

    def OnKeyMove(self, Motion, Mod):
        Move = Motion*10**(int(Mod == 1))
        self.CurrentDisplay.Cursor += Move
        self.OnMove()

    @Update(LocalView)
    def OnMove(self):
        self.CurrentDisplay.OnMove()
        if self.Modes.Build:
            for Component in self.TmpComponents:
                Component.Drag(self.Cursor)
        if self.Modes.Default:
            self.CheckConnexionToggle()
        self.MoveHighlight()

    @Update(LocalView)
    def SetView(self):
        self.CurrentDisplay.SetView()
        self.MoveHighlight()

    @Update(LocalView)
    def NextZoom(self):
        self.DisplayToolbar.children['!checkbutton2'].deselect()
        self.CurrentDisplay.NextZoom()

    @Update(LocalView) 
    def UpdateCursorPlot(self):
        self.CurrentDisplay.UpdateCursorPlot()

    @Update(LocalView)
    def UpdateCursorStyle(self):
        self.CurrentDisplay.UpdateCursorStyle(self.Modes.Current.Color)

    @Update(LocalView)
    def SetWireSymmetry(self, Symmetric):
        self.WireButtons[int(Symmetric)].configure(background = Colors.GUI.Widget.pressed)
        self.WireButtons[1-int(Symmetric)].configure(background = Colors.GUI.Widget.default)
        if Symmetric != self.Library.Wire.DefaultSymmetric:
            self.Library.Wire.DefaultSymmetric = Symmetric
            if self.Modes.Build:
                for Component in self.TmpComponents:
                    if self.Library.IsWire(Component) and Component.Symmetric != Symmetric:
                        Component.Switch()

    def Set(self):
        Joins = self.CH.HasItem(self.Cursor)
        if self.Modes.Build:
            if len(self.TmpComponents) != 1:
                raise Exception(f"{len(self.TmpComponents)} component(s) currently in memory for BuildMode")
            Component = self.TmpComponents.pop()
            if self.CH.Register(Component):
                self.ConfirmComponentRegister(Component, Joins)
            else:
                self.TmpComponents.add(Component)
        elif self.Modes.Default:
            if self.CH.HasItem(self.Cursor) and self.CH.FreeSlot(self.Cursor):
                self.StartComponent(self.Library.Wire)

    @Update(BoardPinsLayout, BoardState)
    def ConfirmComponentRegister(self, Component, Joins):
        self.MoveHighlight()
        if Params.GUI.Behaviour.AutoContinueComponent and (not self.Library.IsWire(Component) or (not Params.GUI.Behaviour.StopWireOnJoin) or not Joins):
            self.StartComponent(Component.__class__, Component.Rotation)
        else:
            self.Modes.Default(Message='end of build')

    @Update(LocalView, CursorInfo)
    def Switch(self):
        if self.Modes.Build:
            for Component in self.TmpComponents:
                Component.Switch()
        elif self.Modes.Default:
            self.NextHighlight()

    @Update(LocalView, CursorInfo)
    def Select(self):
        if self.Highlighted is None:
            return
        if self.Modes.Build:
            self.Modes.Default(Message='selection')
        if self.Modes.Default:
            if not self.Highlighted.Selected:
                self.TmpComponents.update(self.Highlighted.Select())
            else:
                self.TmpComponents.difference_update(self.Highlighted.Fix())
        elif self.Modes.Delete:
            if not self.Highlighted.Removing:
                self.TmpComponents.update(self.Highlighted.StartRemoving())
            else:
                self.TmpComponents.difference_update(self.Highlighted.Fix())

    @Update(LocalView)
    def DeleteSelect(self): # Called when starting delete mode
        if not self.Highlighted is None:
            self.Select()
        for Component in self.TmpComponents:
            Component.StartRemoving()

    @Update(BoardPinsLayout, BoardState, CursorInfo)
    def DeleteConfirm(self): # Called when removing again, actual removing action trigger
        if not self.Highlighted is None and not self.Highlighted.Removing:
            return self.Select()
        if not Params.GUI.Behaviour.AskDeleteConfirmation or self.AskConfirm(f"Do you confirm the deletion of {len(self.TmpComponents)} components ?"):
            self.CH.Remove(self.TmpComponents)
            self.Modes.Default(Message = 'end of delete')
            self.MoveHighlight(Reset = True)

    @Update(LocalView)
    def Rotate(self, var):
        self.Rotation = (self.Rotation + 1) & 0b11
        for Component in self.TmpComponents:
            Component.Rotate()

    @Update(CursorInfo)
    def MoveHighlight(self, Reset = False):
        self.CanHighlight = [Group for Group in self.CH.CursorGroups(self.Cursor) if len(Group.Wires) > 1] \
                            + self.CH.CursorComponents(self.Cursor) \
                            + self.CH.CursorCasings(self.Cursor) # Single item groups would create dual highlight of one component
        if not self.CanHighlight:
            self.CanHighlight = [None]
        if not (self.Highlighted in self.CanHighlight) or Reset:
            self.SwitchHighlight(self.CanHighlight[0])
    def NextHighlight(self):
        self.SwitchHighlight(self.CanHighlight[(self.CanHighlight.index(self.Highlighted)+1)%len(self.CanHighlight)])

    @Update(LocalView, CursorInfo)
    def SwitchHighlight(self, Item):
        if not self.Highlighted is None:
            self.Highlighted.Highlight(False)
        self.Highlighted = Item
        if not Item is None:
            self.Highlighted.Highlight(True)

    @Modes.Default
    def ToggleConnexion(self):
        self.CH.ToggleConnexion(self.Cursor)
        self.MoveHighlight(Reset = True)
    def CheckConnexionToggle(self):
        if self.CH.CanToggleConnexion(self.Cursor):
            self.MainFrame.Board.Controls.ToggleConnexionButton.configure(state = Tk.NORMAL)
        else:
            self.MainFrame.Board.Controls.ToggleConnexionButton.configure(state = Tk.DISABLED)
        if self.CH.CursorConnected(self.Cursor):
            self.MainFrame.Board.Controls.ToggleConnexionButton.configure(image = self._Icons['CrossedDotImage'])
        else:
            self.MainFrame.Board.Controls.ToggleConnexionButton.configure(image = self._Icons['DotImage'])

    def ComputeTruthTable(self):
        NBits = self.CH.NBitsInput
        if NBits == 0:
            Log("Nothing to compute")
            return
        if NBits > Params.GUI.TruthTable.WarningLimitNBits:
            ans = messagebox.askokcancel("Large input", f"Computing truth table for {NBits} bits ({2**NBits} possibilities) ?")
            if not ans:
                return
        self.CurrentBoard.ComputeTruthTable()

# Loading methods

    def LoadGUI(self):
        self._Icons = {}
    
        self.LoadKeys()

        self.MainFrame = SFrame(self.MainWindow)
        self.MainFrame.AddFrame("Top_Panel", 0, 0, columnspan = 3, Side = Tk.LEFT)
        self.MainFrame.AddFrame("Library", 1, 0, Side = Tk.TOP)
        self.MainFrame.AddFrame("Board", 1, 1, Side = Tk.TOP)
        self.MainFrame.AddFrame("Right_Panel", 1, 2, NoName = True)
        self.MainFrame.AddFrame("Console", 2, 0, columnspan = 3, Side = Tk.LEFT)

        self.LoadMenu()
        self.LoadConsole()
        self.LoadTopPanel()
        self.LoadCenterPanel()
        self.LoadRightPanel()
        self.LoadLibraryGUI()

    def CheckFocusOut(self):
        try:
            Focus = self.MainWidget.focus_get()
        except KeyError:
            return
        if (not Focus is None) and (type(Focus) in (Tk.Entry, ConsoleText)) and (not self.Modes.Text):
            self.Modes.Text(Message = 'FocusOut')

    def LoadKeys(self):
        Controls = Params.GUI.Controls
        self.KeysFunctionsDict = {}
        self.MainWindow.bind('<Key>', lambda e: self.TextFilter(self.KeysFunctionsDict.get(e.keysym.lower(), {}).get(e.state, Void), e.keysym.lower(), e.state))

        self.AddControlKey(Controls.Connect, lambda key, mod: self.ToggleConnexion())
        self.AddControlKey(Controls.Close,   lambda key, mod: self.Close(0))
        self.AddControlKey(Controls.Move,    lambda key, mod: self.Move())
        self.AddControlKey(Controls.Restart, lambda key, mod: self.Close(1))
        self.AddControlKey(Controls.Reload,  lambda key, mod: self.Close(2))
        self.AddControlKey(Controls.Rotate,  lambda key, mod: self.Rotate(mod))
        self.AddControlKey(Controls.Select,  lambda key, mod: self.Select())
        self.AddControlKey(Controls.Set,     lambda key, mod: self.Set())
        self.AddControlKey(Controls.Switch,  lambda key, mod: self.Switch())
        for Key in Controls.Moves:
            self.AddControlKey(Key, lambda key, mod: self.OnKeyMove(Params.GUI.Controls.Moves[key], mod))
        for Mode in self.Modes.List:
            if Mode.Key is None:
                continue
            self.AddControlKey(Mode.Key, lambda key, mod, Mode = Mode: Mode(Message='Key'))

        CTRL = 4
        SHIFT = 1
        self.AddControlKey('s', lambda key, mod:self.SaveBoard(), Mod = CTRL)
        self.AddControlKey('s', lambda key, mod:self.SaveBoard(SelectFilename=True), Mod = CTRL+SHIFT)
        self.AddControlKey('o', lambda key, mod:self.Open(New=False), Mod = CTRL)
        self.AddControlKey('n', lambda key, mod:self.Open(New=True), Mod = CTRL)
        self.AddControlKey('w', lambda key, mod:self.CloseBoard(), Mod = CTRL)
        self.AddControlKey('e', lambda key, mod:self.ExportBoardAsComponent(), Mod = CTRL)

    def TextFilter(self, Callback, Symbol, Modifier):
        #if self.MainWindow.focus_get() == self.MainFrame.Console.ConsoleInstance.text and not Symbol in ('escape', 'f4', 'f5', 'f6'): # Hardcoded so far, should be taken from Params as well
        if self.Modes.Text and not Symbol in ('escape', 'f4', 'f5', 'f6'): # Hardcoded so far, should be taken from Params as well
            return
        self.OnKeyRegistration(Callback, Symbol, Modifier)

    def AddControlKey(self, Key, Callback, Mod = 0):
        if not Key in self.KeysFunctionsDict:
            self.KeysFunctionsDict[Key] = {}
        if Mod in self.KeysFunctionsDict[Key]:
            raise ValueError(f"Used key : {bool(Mod)*(('', 'Ctrl', 'Shift')[Mod]+'+')}{Key}")
        self.KeysFunctionsDict[Key][Mod] = Callback

    def LoadMenu(self):
        def AddCommand(Menu, Label, Callback, *args, **kwargs):
            Menu.add_command(label = Label, command = lambda:self.OnStaticGUIButton(Callback, *args, **kwargs))

        MainMenu = Tk.Menu(self.MainWindow)
        FMenu = Tk.Menu(MainMenu, tearoff=0)

        AddCommand(FMenu, 'New', self.Open, New = True)
        AddCommand(FMenu, 'Open', self.Open, Ask = False)
        AddCommand(FMenu, 'Save', self.SaveBoard)
        AddCommand(FMenu, 'Save as...', self.SaveBoard, SelectFilename = True)
        FMenu.add_separator()
        AddCommand(FMenu, 'Export as component', self.ExportBoardAsComponent)
        FMenu.add_command(label="Exit", command=self.Close)
        MainMenu.add_cascade(label="File", menu=FMenu)

        EMenu = Tk.Menu(MainMenu, tearoff=0)
        AddCommand(EMenu, "Undo", self.Undo)
        AddCommand(EMenu, "Undo", self.Options)
        MainMenu.add_cascade(label="Edit", menu=EMenu)

        HMenu = Tk.Menu(MainMenu, tearoff=0)
        AddCommand(HMenu, "Help Index", Void)
        AddCommand(HMenu, "About...", self.About)
        MainMenu.add_cascade(label="Help", menu=HMenu)

        self.MainWindow.config(menu=MainMenu)

    def Undo(self):
        raise NotImplementedError
    def Options(self):
        raise NotImplementedError
    def About(self):
        raise NotImplementedError

    def LoadConsole(self):
        ConsoleInstance = ConsoleWidget(self.MainFrame.Console.frame, locals(), self.MainWindow.destroy)
        ConsoleInstance.pack(fill=Tk.BOTH, expand=True)
        self.MainFrame.Console.RemoveDefaultName()
        self.MainFrame.Console.AdvertiseChild(ConsoleInstance, "ConsoleInstance")
        #ConsoleInstance.text.bind('<FocusIn>', lambda e:self.Modes.Text(Message = 'Console FocusIn'))

    def LoadTopPanel(self):
        self.LoadUpdateFunctions()
        self.LoadTruthTableWidgets()

    def LoadUpdateFunctions(self):
        UpdateFrame = self.MainFrame.Top_Panel.AddFrame("UpdateFunctions", Side = Tk.TOP, NoName = True)
        UpdateFrame.AddWidget(Tk.Button, "Pins_layout", text = "Pins layout", command = self.BoardPinsLayout, width = 20)
        UpdateFrame.AddWidget(Tk.Button, "Cursor_info", text = "Cursor info", command = self.CursorInfo, width = 20)
        UpdateFrame.AddWidget(Tk.Button, "Board_state", text = "Board state", command = self.BoardState, width = 20)
        UpdateFrame.AddWidget(Tk.Button, "Local_view", text = "Local view", command = self.LocalView, width = 20)

    def LoadTruthTableWidgets(self):
        TTFrame = self.MainFrame.Top_Panel.AddFrame("TruthTable", Side = Tk.TOP, NoName = True)
        TTFrame.AddWidget(Tk.Button, "Compute", text = "Compute truth table", command = self.ComputeTruthTable, width = 20)

    def LoadCenterPanel(self):
        self.MainFrame.Board.AddFrame("Controls", Side = Tk.LEFT)
        self.MainFrame.Board.AddFrame("View")
        self.MainFrame.Board.AddFrame("DisplayToolbar", Side = Tk.LEFT)
        
        BoardDisplayC.frame = self.MainFrame.Board.View.frame

        self.LoadControls()

        self.NewDisplay()
        self.SelectDisplay(self.LoadedDisplays[-1])

        self.LoadDisplayToolbar()

    def LoadControls(self):
        self._Icons['WSImage'] = Tk.PhotoImage(file="./images/WireStraight.png")
        self.MainFrame.Board.Controls.AddWidget(Tk.Button, "WireStraight", image=self._Icons['WSImage'], height = 30, width = 30, command = lambda:self.OnStaticGUIButton(self.SetWireSymmetry, False))
        self._Icons['WDImage'] = Tk.PhotoImage(file="./images/WireDiagonal.png")
        self.MainFrame.Board.Controls.AddWidget(Tk.Button, "WireDiagonal", image=self._Icons['WDImage'], height = 30, width = 30, command = lambda:self.OnStaticGUIButton(self.SetWireSymmetry, True))
        self.WireButtons = (self.MainFrame.Board.Controls.WireStraight, self.MainFrame.Board.Controls.WireDiagonal)
        self.SetWireSymmetry(Params.GUI.Behaviour.DefaultWireSymmetric)
        self._Icons['DotImage'] = Tk.PhotoImage(file="./images/Dot.png").subsample(10)
        self._Icons['CrossedDotImage'] = Tk.PhotoImage(file="./images/CrossedDot.png").subsample(10)
        self.MainFrame.Board.Controls.AddWidget(Tk.Button, "ToggleConnexionButton", image=self._Icons['DotImage'], height = 30, width = 30, state = Tk.DISABLED, command = lambda:self.OnStaticGUIButton(self.ToggleConnexion))

        self.MainFrame.Board.Controls.AddWidget(ttk.Separator, orient = 'vertical')

        self._Icons['RLImage'] = Tk.PhotoImage(file="./images/RotateLeft.png").subsample(8)
        self.MainFrame.Board.Controls.AddWidget(Tk.Button, "RotateLeft", image=self._Icons['RLImage'], height = 30, width = 30, command = lambda:self.OnStaticGUIButton(self.Rotate, 0))
        self._Icons['RRImage'] = Tk.PhotoImage(file="./images/RotateRight.png").subsample(8)
        self.MainFrame.Board.Controls.AddWidget(Tk.Button, "RotateRight", image=self._Icons['RRImage'], height = 30, width = 30, command = lambda:self.OnStaticGUIButton(self.Rotate, 1))

        BoardSelectionFrame = self.MainFrame.Board.Controls.AddFrame("BoardSelectionFrame", Side = Tk.LEFT)
        self.BoardVar = Tk.StringVar(BoardSelectionFrame.frame, self.NewBoardStr)
        #self.BoardVar.trace_add("write", lambda *args, self = self, **kwargs: self.MenuSelectBoardName(self.BoardVar.get()))
        self.BoardsMenu = BoardSelectionFrame.AddWidget(Tk.OptionMenu, variable = self.BoardVar, value = self.BoardVar.get(), command = self.MenuSelectBoardName)
        self.BoardsMenu.configure(width = Params.GUI.CenterPanel.BoardMenuWidth)
#        self.BoardsMenu.configure(justify = 'left')

        self._Icons['Cross'] = Tk.PhotoImage(file="./images/Cross.png").subsample(40)
        BoardSelectionFrame.AddWidget(Tk.Button, "CloseBoard", image = self._Icons['Cross'], height = 30, width = 30, command = lambda:self.OnStaticGUIButton(self.CloseBoard))
        self._Icons['Component'] = Tk.PhotoImage(file="./images/Component.png").subsample(7)
        BoardSelectionFrame.AddWidget(Tk.Button, "ToComponent", image = self._Icons['Component'], height = 30, width = 30, command = lambda:self.OnStaticGUIButton(self.ExportBoardAsComponent))

    def LoadDisplayToolbar(self):
        self.MainFrame.Board.DisplayToolbar.AddFrame("Buttons", Side = Tk.TOP, Border = False)
        self.MainFrame.Board.DisplayToolbar.AddFrame("Labels", Border = False)
        self.MainFrame.Board.DisplayToolbar.Buttons.RemoveDefaultName()
        self.DisplayToolbar = NavigationToolbar2Tk(self.CurrentDisplay.Canvas, self.MainFrame.Board.DisplayToolbar.Buttons.frame)
        NewCommands = {'!button':lambda:self.OnStaticGUIButton(self.SetView), # Remap Home button
                        '!checkbutton2':lambda:self.OnStaticGUIButton(self.NextZoom) # Remap zoom button
        }
        RemovedButtons = ('!button2', # Left arrow
                          '!button3', # Right arrow
                          '!button4', # Configure Subplots
                          '!button5', # Save
                          '!label2') # Mouse location
                          
        for button in RemovedButtons:
            self.DisplayToolbar.children[button].pack_forget()
            del self.DisplayToolbar.children[button]
        for button, command in NewCommands.items():
            self.DisplayToolbar.children[button].config(command=command)
        self.DisplayToolbar.update()
        self.MainFrame.Board.DisplayToolbar.Labels.AddWidget(Tk.Label, "CursorLabel", row = 0, column = 0, text = "")
        self.MainFrame.Board.DisplayToolbar.Labels.AddWidget(Tk.Label, "HighlightLabel", row = 1, column = 0, text = "")

    def LoadRightPanel(self):
        self.MainFrame.Right_Panel.AddFrame("Board_Inputs", row = 0, column = 0, columnspan = 2, Border = True, NoName = True)
        self.BoardInputEntry = SEntry(self.MainFrame.Right_Panel.Board_Inputs, "Board Input", Bits = tuple(), TotalWidth = Params.GUI.RightPanel.Width)
        self.MainFrame.Right_Panel.AddFrame("Board_Outputs", row = 1, column = 0, columnspan = 2, Border = True, NoName = True)
        self.BoardOutputLabel = SLabel(self.MainFrame.Right_Panel.Board_Outputs, "Board Output", Bits = tuple(), TotalWidth = Params.GUI.RightPanel.Width)
        
        self.BoardInputWidgets =  {self.BoardInputEntry}
        self.BoardOutputWidgets = {self.BoardOutputLabel}

        self.MainFrame.Right_Panel.AddFrame("Input_Groups", row = 2, column = 0, Border = True, NameDisplayed = True, Width = Params.GUI.RightPanel.Width//2)
        self.MainFrame.Right_Panel.AddFrame("Input_Pins", row = 3, column = 0, Border = True, NameDisplayed = True, Width = Params.GUI.RightPanel.Width//2)
        self.MainFrame.Right_Panel.AddFrame("Output_Groups", row = 2, column = 1, Border = True, NameDisplayed = True, Width = Params.GUI.RightPanel.Width//2)
        self.MainFrame.Right_Panel.AddFrame("Output_Pins", row = 3, column = 1, Border = True, NameDisplayed = True, Width = Params.GUI.RightPanel.Width//2)

    def LoadLibraryGUI(self):
        self.CompToButtonMap = {}
        self.CurrentCompButton = None
        for BookName in self.Library.Books:
            Book = getattr(self.Library, BookName)
            BookFrame = self.MainFrame.Library.AddFrame(BookName, Side = Tk.TOP, NameDisplayed = True)
            CompFrame = BookFrame.AddFrame("CompFrame", NameDisplayed = False)
            for nComp, CompName in enumerate(Book.Components):
                row = nComp // Params.GUI.Library.Columns
                column = nComp % Params.GUI.Library.Columns
                CompClass = getattr(Book, CompName)
                ControlKey = getattr(Book, 'key_'+CompName)
                Add = ''
                if ControlKey:
                    Add = f' ({ControlKey})'
                    self.AddControlKey(ControlKey, lambda key, mod, CompClass = CompClass: self.StartComponent(CompClass))
                self.CompToButtonMap[CompClass] = CompFrame.AddWidget(Tk.Button, f"{BookName}.{CompName}", row = row, column = column, text = CompName+Add, height = Params.GUI.Library.ComponentHeight, 
                                                                        command = lambda CompClass = CompClass: self.OnComponentButtonClick(CompClass))

    def SetLibraryButtonColor(self, Button):
        if Button == self.CurrentCompButton:
            return
        if not self.CurrentCompButton is None:
            self.CurrentCompButton.configure(background = Colors.GUI.Widget.default)
        self.CurrentCompButton = Button
        if not self.CurrentCompButton is None:
            self.CurrentCompButton.configure(background = Colors.GUI.Widget.pressed)

    def Close(self, Restart = 0):
        self.MainWindow.quit()
        self.Restart = Restart
        #self.MainWindow.destroy()

if __name__ == '__main__':
    Args = sys.argv
    print(Args)
    G = GUI(Args)
    if G.Restart:
        print("Restarting")
    sys.exit([0, 5, 6][G.Restart])

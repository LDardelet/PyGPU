import tkinter as Tk
from tkinter import ttk
from PIL import Image
import os, sys
import sys
import numpy as np

import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from Console import ConsoleWidget, Log, LogSuccess, LogWarning, LogError
from Values import Colors, Params, PinDict
from Tools import Void, ModesDict, ModeC, SFrame, SEntry, SLabel, SPinEntry, BoardIOWidgetBase
import Circuit
import Storage

matplotlib.use("TkAgg")

class GUI:
    Modes = ModesDict() # Here as we need mode decorator
    UpdateFunctions = {}
    UpdateLocked = False

    def Trigger(func):
        def Wrap(self, *args, **kwargs):
            UpdateWhenFinished = False
            if not self.UpdateLocked:
                self.UpdateLocked = True
                UpdateWhenFinished = True
            else:
                print(f"Trigger ignored : {func.__name__}")
            res = func(self, *args, **kwargs)
            if UpdateWhenFinished:
                self.SolveUpdateRequests(func)
            return res
        return Wrap
    def Update(*UpdateFunctions):
        def Wrapper(func):
            def Wrap(self, *args, **kwargs):
                for UpdateFunction in UpdateFunctions:
                    if UpdateFunction in self.UpdateFunctions:
                        self.UpdateFunctions[UpdateFunction].add(func.__name__)
                    else:
                        self.UpdateFunctions[UpdateFunction] = {func.__name__}
                return func(self, *args, **kwargs)
            return Wrap
        return Wrapper

    def LocalView(self):                                # Update of the plot (colors, style, ... with no effect on the cursor, the highlight or the level values
        self.DisplayCanvas.draw()
    def BoardState(self): # Formerly Draw()
        for BoardInputWidget in self.BoardInputWidgets:
            BoardInputWidget.Pull(self.CH.Input, self.CH.InputValid)
        if self.CH.LiveUpdate:
            for BoardOutputWidget in self.BoardOutputWidgets:
                BoardOutputWidget.Pull(self.CH.Output, self.CH.OutputValid)
        self.DisplayCanvas.draw()
    def CursorInfo(self):
        GroupsInfo = self.CH.GroupsInfo(self.Cursor)
        self.MainFrame.Board.DisplayToolbar.Labels.CursorLabel['text'] = f"{self.Cursor.tolist()}" + bool(GroupsInfo)*": " + self.CH.GroupsInfo(self.Cursor)
        if self.Highlighted is None:
            Info = ""
        else:
            Info = str(self.Highlighted)
        self.MainFrame.Board.DisplayToolbar.Labels.HighlightLabel['text'] = f"Highlight: {Info}"
    def GUILayout(self): # Formerly CheckBoardPins()
        for Pin, PinEntry in list(self.SetupPins.items()):
            if Pin not in self.CH.Pins:
                if Pin.Type == PinDict.Input or PinEntry.Type != Pin.Type:
                    self.MainFrame.Right_Panel.Input_Pins.Destroy(f"PinFrame{Pin.ID}")
                else:
                    self.MainFrame.Right_Panel.Output_Pins.Destroy(f"PinFrame{Pin.ID}")
                del self.SetupPins[Pin]
            else: # We ensure the pin is in the right location
                PinEntry.Bits = (Pin.TypeIndex, )
        for Pin in self.CH.Pins:
            if Pin not in self.SetupPins:
                if Pin.Type == PinDict.Input:
                    PinFrame = self.MainFrame.Right_Panel.Input_Pins.AddFrame(f"PinFrame{Pin.ID}", row = Pin.TypeIndex+1, column = 0, Border = True, NoName = True)
                    PinSet = self.BoardInputWidgets
                else:
                    PinFrame = self.MainFrame.Right_Panel.Output_Pins.AddFrame(f"PinFrame{Pin.ID}", row = Pin.TypeIndex+1, column = 0, Border = True, NoName = True)
                    PinSet = self.BoardOutputWidgets
                PinEntry = SPinEntry(PinFrame.frame, Pin)
                self.SetupPins[Pin] = PinEntry
                PinSet.add(PinEntry)
        self.BoardInputEntry.Bits = tuple(range(len(self.CH.InputPins)))
        self.BoardOutputLabel.Bits = tuple(range(len(self.CH.OutputPins)))

    def SolveUpdateRequests(self, func):
        if not self.UpdateFunctions:
            print(f"{func.__name__} induced no update")
        else:
            print(f"Updates triggered by {func.__name__}:")
            while self.UpdateFunctions:
                UpdateFunction, Callers = self.UpdateFunctions.popitem()
                print(f" -> {UpdateFunction.__name__} called by {', '.join(Callers)}")
                UpdateFunction(self)
        self.UpdateLocked = False

    def __init__(self, Args):
        self.MainWindow = Tk.Tk()

#        def ReturnCallback(Entry):
#            self.Modes.Default(Message = f'Entry return by {Entry}')
#
#        def LevelModificationCallback(Entry):
#            self.SetBoardInput(Entry.Push(self.CH.Input))
#
#       BoardIOWidgetBase.ReturnCallback = ReturnCallback
#       BoardIOWidgetBase.LevelModificationCallback = LevelModificationCallback
        
        BoardIOWidgetBase.GUI = self
        ModeC.GUI = self
        self.Library = Circuit.CLibrary()
        self.FH = Storage.FileHandlerC()

        self.LoadGUI()

        self.Circuit = Circuit
        if len(Args) > 1:
            self.LoadBoardData(Args[1])
        else:
            self.LoadBoardData()

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
    def BoardIOWidgetLevelModificationCallback(self, Entry):
        self.SetBoardInput(Entry.Push(self.CH.Input))

    @Trigger  # TODO : merge all callback functions to OnUserAction
    def OnStaticGUIButton(self, Callback, *args, **kwargs):
        return Callback(self, *args, **kwargs)

    @Trigger
    def OnKeyRegistration(self, Callback, Key, Mod):
        Callback(Key, Mod)

    @Trigger
    def OnComponentButtonClick(self, ComponentClass):
        self.StartComponent(ComponentClass)

    # Update functions. No trigger should be within here, apart from simulation run

    def ClearBoard(self):
        self.CH.LiveUpdate = False # Possibly useless
        self.DisplayAx.cla()
        self.PlotView()
        return True

    @Modes.Default
    def SaveBoardData(self, SelectFilename = False):
        if self.FH.Filename is None or SelectFilename:
            Filename = Tk.filedialog.asksaveasfilename(initialdir = os.path.abspath(Params.GUI.DataAbsPath + Params.GUI.BoardSaveSubfolder), filetypes=[('BOARD file', '.brd')], defaultextension = '.brd')
            if not Filename is None:
                self.FH.Filename = Filename
                self.SetTitle()
        self.ClearTmpComponents()
        self.FH.Save(handler = self.CH)

    def Open(self, Ask):
        if self.CH._Modified:
            return
        self.ClearBoard()
        if Ask:
            Filename = Tk.filedialog.askopenfilename(initialdir = os.path.abspath(Params.GUI.DataAbsPath + Params.GUI.BoardSaveSubfolder), filetypes=[('BOARD file', '.brd')], defaultextension = '.brd')
            if not Filename is None:
                self.LoadBoardData(Filename)
        else:
            self.LoadBoardData()

    @Update(BoardState)
    def SetBoardInput(self, Input):
        self.CH.Input = Input

    @Update(GUILayout, BoardState)
    def LoadBoardData(self, Filename = None):
        if not os.path.exists(Params.GUI.DataAbsPath + Params.GUI.BoardSaveSubfolder):
            os.mkdir(Params.GUI.DataAbsPath + Params.GUI.BoardSaveSubfolder)

        if Filename is None:
            self.FH.Filename = None
            self.CH = Circuit.ComponentsHandlerC()
        else:
            D = self.FH.Load(Filename)
            self.CH = D['handler']
        self.SetTitle()

        self.Rotation = 0
        self.CanHighlight = [None]
        self.Highlighted = None
        self.TmpComponents = set()
        self.SetupPins = {}
        self.UpdateLocked = False

        self.SetView()

    def SetTitle(self):
        if self.FH.Filename is None:
            BoardName = 'New'
        else:
            BoardName = self.FH.Filename.split('/')[-1]
        self.MainWindow.title(Params.GUI.Name + f" ({BoardName})")

    @Update(LocalView)
    @Modes.Build
    def StartComponent(self, CClass):
        self.SetLibraryButtonColor(self.CompToButtonMap[CClass])
        self.TmpComponents.add(CClass(self.Cursor, self.Rotation))

    @Update(LocalView)
    def ClearTmpComponents(self):
        while self.TmpComponents:
            self.TmpComponents.pop().Clear()

    def OnKeyMove(self, Motion, Mod):
        Move = Motion*10**(int(Mod == 1))
        self.Cursor += Move
        self.OnMove()

    @Update(LocalView)
    def OnMove(self):
        self.UpdateCursorPlot()
        Displacement = np.maximum(0, self.Cursor + Params.GUI.View.DefaultMargin - (self.LeftBotLoc + self.Size))
        if Displacement.any():
            self.LeftBotLoc += Displacement
            self.SetBoardLimits()
        else:
            Displacement = np.maximum(0, self.LeftBotLoc - (self.Cursor - Params.GUI.View.DefaultMargin))
            if Displacement.any():
                self.LeftBotLoc -= Displacement
                self.SetBoardLimits()
        self.MoveHighlight()
        if self.Modes.Build:
            for Component in self.TmpComponents:
                Component.Drag(self.Cursor)
        if self.Modes.Default:
            self.CheckConnexionToggle()

    def SetView(self, View = None):
        if View is None:
            self.Size = Params.GUI.View.Zooms[0]
            if (self.CH.ComponentsLimits == 0).all():
                self.Size = Params.GUI.View.Zooms[0]
            else:
                self.Size = max(Params.GUI.View.Zooms[0], (self.CH.ComponentsLimits[:,1] - self.CH.ComponentsLimits[:,0]).max())
            self.Cursor = self.CH.ComponentsLimits.mean(axis = 1).astype(int)
            self.LeftBotLoc = self.Cursor - (self.Size // 2)
        else:
            raise NotImplementedError
        self.SetBoardLimits()
        
        self.UpdateCursorPlot()
        self.MoveHighlight()

    def NextZoom(self):
        self.DisplayToolbar.children['!checkbutton2'].deselect()
        if self.Size not in Params.GUI.View.Zooms:
            self.Size = Params.GUI.View.Zooms[0]
        else:
            self.Size = Params.GUI.View.Zooms[(Params.GUI.View.Zooms.index(self.Size)+1)%len(Params.GUI.View.Zooms)]
        self.LeftBotLoc = self.Cursor - (self.Size // 2)
        self.SetBoardLimits()

    @Update(LocalView) 
    def UpdateCursorPlot(self):
        self.Plots['Cursor'].set_data(*self.Cursor)
        if Params.GUI.View.CursorLinesWidth:
            self.Plots['HCursor'].set_data([-Params.Board.Max, Params.Board.Max], [self.Cursor[1], self.Cursor[1]])
            self.Plots['VCursor'].set_data([self.Cursor[0], self.Cursor[0]], [-Params.Board.Max, Params.Board.Max])

    @Update(LocalView)
    def UpdateCursorStyle(self):
        Color = self.Modes.Current.Color
        self.Plots['Cursor'].set_color(Color)
        if Params.GUI.View.CursorLinesWidth:
            self.Plots['HCursor'].set_color(Color)
            self.Plots['VCursor'].set_color(Color)

    @Update(LocalView)
    def SetBoardLimits(self):
        self.DisplayAx.set_xlim(self.LeftBotLoc[0],self.LeftBotLoc[0]+self.Size)
        self.DisplayAx.set_ylim(self.LeftBotLoc[1],self.LeftBotLoc[1]+self.Size)

    @Update(LocalView)
    def SetWireBuildMode(self, mode):
        self.WireButtons[mode].configure(background = Colors.GUI.Widget.pressed)
        self.WireButtons[1-mode].configure(background = Colors.GUI.Widget.default)
        if mode != self.Library.Wire.BuildMode:
            self.Library.Wire.BuildMode = mode
            if self.Modes.Build:
                for Component in self.TmpComponents:
                    if self.Library.IsWire(Component):
                        Component.Switch()

    @Update(GUILayout)
    def Set(self):
        Joins = self.CH.HasItem(self.Cursor)
        if self.Modes.Build:
            if len(self.TmpComponents) != 1:
                raise Exception(f"{len(self.TmpComponents)} component(s) currently in memory for BuildMode")
            Component = self.TmpComponents.pop()
            if self.CH.Register(Component):
                self.MoveHighlight()
                self.ConfirmComponentRegister(Component)
            else:
                self.TmpComponents.add(Component)
        elif self.Modes.Default:
            if self.CH.HasItem(self.Cursor) and self.CH.FreeSlot(self.Cursor):
                self.StartComponent(self.Library.Wire)

    @Update(GUILayout)
    def ConfirmComponentRegister(self, Component):
        if Params.GUI.Behaviour.AutoContinueComponent and (not self.Library.IsWire(Component) or (not Params.GUI.Behaviour.StopWireOnJoin) or not Joins):
            self.StartComponent(Component.__class__)
        else:
            self.Modes.Default(Message='end of build')

    @Update(LocalView, CursorInfo)
    def Switch(self):
        if self.Modes.Build:
            for Component in self.TmpComponents:
                Component.Switch()
                if self.Library.IsWire(Component):
                    self.SetWireBuildMode(self.Library.Wire.BuildMode)
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

    @Update(GUILayout, BoardState, CursorInfo)
    def DeleteConfirm(self): # Called when removing again, actual removing action trigger
        if not self.Highlighted is None and not self.Highlighted.Removing:
            return self.Select()
        if not Params.GUI.Behaviour.AskDeleteConfirmation or self.AskConfirm(f"Do you confirm the deletion of {len(self.TmpComponents)} components ?"):
            self.CH.Remove(self.TmpComponents)
            self.TmpComponents = set()
            self.Modes.Default(Message = 'end of delete')

    @Update(LocalView)
    def Rotate(self, var):
        self.Rotation = (self.Rotation + 1) & 0b11
        for Component in self.TmpComponents:
            Component.Rotate()

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

    @Update(LocalView)
    def PlotView(self):
        self.Plots = {}
        self.Plots['Cursor'] = self.DisplayAx.plot(0,0, marker = 'o', color = self.Modes.Current.Color)[0]
        if Params.GUI.View.CursorLinesWidth:
            self.Plots['HCursor'] = self.DisplayAx.plot([-Params.Board.Max, Params.Board.Max], [0,0], linewidth = Params.GUI.View.CursorLinesWidth, color = self.Modes.Current.Color, alpha = 0.3)[0]
            self.Plots['VCursor'] = self.DisplayAx.plot([0,0], [-Params.Board.Max, Params.Board.Max], linewidth = Params.GUI.View.CursorLinesWidth, color = self.Modes.Current.Color, alpha = 0.3)[0]
        RLE = Params.GUI.View.RefLineEvery
        if RLE:
            NLines = Params.Board.Size // RLE
            self.Plots['HLines']=[self.DisplayAx.plot([-Params.Board.Max, Params.Board.Max], 
                                 [nLine*RLE, nLine*RLE], color = Colors.GUI.default, alpha = 0.2)[0] for nLine in range(-NLines//2+1, NLines//2)]
            self.Plots['VLines']=[self.DisplayAx.plot([nLine*RLE, nLine*RLE], 
                                 [-Params.Board.Max, Params.Board.Max], color = Colors.GUI.default, alpha = 0.2)[0] for nLine in range(-NLines//2+1, NLines//2)]

# Loading methods

    def LoadGUI(self):
        self._Icons = {}
    
        self.LoadKeys()

        self.MainFrame = SFrame(self.MainWindow)
        self.MainFrame.AddFrame("Top_Panel", 0, 0, columnspan = 3)
        self.MainFrame.AddFrame("Library", 1, 0, Side = Tk.TOP)
        self.MainFrame.AddFrame("Board", 1, 1, Side = Tk.TOP)
        self.MainFrame.AddFrame("Right_Panel", 1, 2, NoName = True)
        self.MainFrame.AddFrame("Console", 2, 0, columnspan = 3, Side = Tk.LEFT)

        self.LoadMenu()
        self.LoadConsole()
        self.LoadCenterPanel()
        self.LoadRightPanel()
        self.LoadLibraryGUI()

        self.MainWidget.focus_set()
        self.MainWidget.bind('<FocusOut>', lambda e:self.CheckFocusOut())

    def CheckFocusOut(self):
        Focus = self.MainWidget.focus_get()
        if not Focus is None and not self.Modes.Text:
            self.Modes.Text(Message = 'FocusOut')

    def LoadKeys(self):
        Controls = Params.GUI.Controls
        self.KeysFunctionsDict = {}
        self.MainWindow.bind('<Key>', lambda e: self.TextFilter(self.KeysFunctionsDict.get(e.keysym.lower(), {}).get(e.state, Void), e.keysym.lower(), e.state))

        self.AddControlKey(Controls.Connect, lambda key, mod: self.ToggleConnexion())
        self.AddControlKey(Controls.Close,   lambda key, mod: self.Close(0))
#        self.AddControlKey(Controls.Delete,  lambda key, mod: self.Delete())
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
        self.AddControlKey('s', lambda key, mod:self.SaveBoardData(), Mod = CTRL)
        self.AddControlKey('s', lambda key, mod:self.SaveBoardData(SelectFilename=True), Mod = CTRL+SHIFT)
        self.AddControlKey('o', lambda key, mod:self.Open(Ask=True), Mod = CTRL)
        self.AddControlKey('n', lambda key, mod:self.Open(Ask=False), Mod = CTRL)

        #self.MainWindow.bind('<Key>', lambda e: print(e.__dict__)) # Override to check key value

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

        AddCommand(FMenu, 'New', self.Open, Ask = False)
        AddCommand(FMenu, 'Open', self.Open, Ask = True)
        AddCommand(FMenu, 'Save', self.SaveBoardData)
        AddCommand(FMenu, 'Save as...', self.SaveBoardData, SelectFilename = True)
        FMenu.add_separator()
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

    def LoadCenterPanel(self):
        self.MainFrame.Board.AddFrame("Controls", Side = Tk.LEFT)
        self.MainFrame.Board.AddFrame("View")
        self.MainFrame.Board.AddFrame("DisplayToolbar", Side = Tk.LEFT)
        self.LoadControls()
        self.LoadView()
        self.LoadDisplayToolbar()

    def LoadControls(self):
        self._Icons['WSImage'] = Tk.PhotoImage(file="./images/WireStraight.png")
        self.MainFrame.Board.Controls.AddWidget(Tk.Button, "WireStraight", image=self._Icons['WSImage'], height = 30, width = 30, command = lambda:self.OnStaticGUIButton(self.SetWireBuildMode, 0))
        self._Icons['WDImage'] = Tk.PhotoImage(file="./images/WireDiagonal.png")
        self.MainFrame.Board.Controls.AddWidget(Tk.Button, "WireDiagonal", image=self._Icons['WDImage'], height = 30, width = 30, command = lambda:self.OnStaticGUIButton(self.SetWireBuildMode, 1))
        self.WireButtons = (self.MainFrame.Board.Controls.WireStraight, self.MainFrame.Board.Controls.WireDiagonal)
        self.SetWireBuildMode(Params.GUI.Behaviour.DefaultWireBuildMode)
        self._Icons['DotImage'] = Tk.PhotoImage(file="./images/Dot.png").subsample(10)
        self._Icons['CrossedDotImage'] = Tk.PhotoImage(file="./images/CrossedDot.png").subsample(10)
        self.MainFrame.Board.Controls.AddWidget(Tk.Button, "ToggleConnexionButton", image=self._Icons['DotImage'], height = 30, width = 30, state = Tk.DISABLED, command = lambda:self.OnStaticGUIButton(self.ToggleConnexion))

        self.MainFrame.Board.Controls.AddWidget(ttk.Separator, orient = 'vertical')

        self._Icons['RLImage'] = Tk.PhotoImage(file="./images/RotateLeft.png").subsample(8)
        self.MainFrame.Board.Controls.AddWidget(Tk.Button, "RotateLeft", image=self._Icons['RLImage'], height = 30, width = 30, command = lambda:self.OnStaticGUIButton(self.Rotate, 0))
        self._Icons['RRImage'] = Tk.PhotoImage(file="./images/RotateRight.png").subsample(8)
        self.MainFrame.Board.Controls.AddWidget(Tk.Button, "RotateRight", image=self._Icons['RRImage'], height = 30, width = 30, command = lambda:self.OnStaticGUIButton(self.Rotate, 1))

    def LoadView(self):
        self.DisplayFigure = matplotlib.figure.Figure(figsize=Params.GUI.View.FigSize, dpi=Params.GUI.View.DPI)
        self.DisplayFigure.subplots_adjust(0., 0., 1., 1.)
        self.DisplayAx = self.DisplayFigure.add_subplot(111)
        self.DisplayAx.set_aspect("equal")
        self.DisplayAx.tick_params('both', left = False, bottom = False, labelleft = False, labelbottom = False)
        self.DisplayAx.set_facecolor((0., 0., 0.))

        self.DisplayCanvas = matplotlib.backends.backend_tkagg.FigureCanvasTkAgg(self.DisplayFigure, self.MainFrame.Board.View.frame)
        self.DisplayCanvas.draw()
        self.DisplayCanvas.mpl_connect('button_press_event', lambda e:self.OnClickMove(np.array([e.xdata, e.ydata])))

        self.MainFrame.Board.View.AdvertiseChild(self.DisplayCanvas.get_tk_widget(), "Plot")
        self.MainFrame.Board.View.Plot.grid(row = 0, column = 0)
        self.Library.ComponentBase.Display = self.DisplayAx

        self.PlotView()

        self.MainWidget = self.DisplayCanvas.get_tk_widget()

    def LoadDisplayToolbar(self):
        self.MainFrame.Board.DisplayToolbar.AddFrame("Buttons", Side = Tk.TOP, Border = False)
        self.MainFrame.Board.DisplayToolbar.AddFrame("Labels", Border = False)
        self.MainFrame.Board.DisplayToolbar.Buttons.RemoveDefaultName()
        self.DisplayToolbar = NavigationToolbar2Tk(self.DisplayCanvas, self.MainFrame.Board.DisplayToolbar.Buttons.frame)
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
        self.BoardInputEntry = SEntry(self.MainFrame.Right_Panel.Board_Inputs.frame, "Board Input", Bits = tuple(), TotalWidth = Params.GUI.RightPanel.Width)
        self.MainFrame.Right_Panel.AddFrame("Board_Outputs", row = 1, column = 0, columnspan = 2, Border = True, NoName = True)
        self.BoardOutputLabel = SLabel(self.MainFrame.Right_Panel.Board_Outputs.frame, "Board Output", Bits = tuple(), TotalWidth = Params.GUI.RightPanel.Width)

        self.BoardInputWidgets =  {self.BoardInputEntry}
        self.BoardOutputWidgets = {self.BoardOutputLabel}

        self.MainFrame.Right_Panel.AddFrame("Input_Pins", row = 2, column = 0, Border = True, NameDisplayed = True, Width = Params.GUI.RightPanel.Width//2)
        self.MainFrame.Right_Panel.AddFrame("Output_Pins", row = 2, column = 1, Border = True, NameDisplayed = True, Width = Params.GUI.RightPanel.Width//2)

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

import tkinter as Tk
from tkinter import ttk
from PIL import Image
import os
import sys
import numpy as np

import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from Console import ConsoleWidget, Log, LogSuccess, LogWarning, LogError
from Values import Colors, Params
import Circuit
import Storage

matplotlib.use("TkAgg")

class GUI:
    def __init__(self):
        self.MainWindow = Tk.Tk()
        self.MainWindow.title('Logic Gates Simulator')

        self.LoadGUIModes()
        self.Library = Circuit.CLibrary()

        self.LoadGUI()

        self.LoadBoardData()


        self.MainWindow.mainloop()

    def LoadGUIModes(self):
        class DefaultModeC(ModeC):
            ID = 0
            def SetProps(self):
                self.CheckConnexionAvailable()
            def LeaveProps(self):
                self.MainFrame.Board.Controls.ToggleConnexion.configure(state = Tk.DISABLED)
            def ReloadProps(self):
                self.ClearTmpComponent()
                self.DisplayFigure.canvas.draw()
        class ConsoleModeC(ModeC):
            ID = 1
            def SetProps(self):
                self.MainFrame.Console.ConsoleInstance.text.see(Tk.END)
                if self.MainWindow.focus_get() != self.MainFrame.Console.ConsoleInstance.text:
                    self.MainFrame.Console.ConsoleInstance.text.focus_set()
            def LeaveProps(self):
                self.MainWindow.focus_set()
        class BuildModeC(ModeC):
            ID = 2
            def SetProps(self):
                self.Plots['Cursor'].set_alpha(Params.GUI.Cursor.HiddenAlpha)
            def LeaveProps(self):
                self.Plots['Cursor'].set_alpha(Params.GUI.Cursor.DefaultAlpha)
                self.SelectLibComponent(None)
            def ReloadProps(self):
                self.ClearTmpComponent()
        class ModesDict:
            Default = DefaultModeC()
            Console = ConsoleModeC()
            Build =   BuildModeC()
            def __init__(self):
                self.List = (self.Default, self.Console, self.Build)
            @property
            def Current(self):
                return ModeC.Current

        ModeC.GUI = self
        self.Modes = ModesDict()

    def ClearBoard(self):
        self.CH.LiveUpdate = False # Possibly useless
        self.DisplayAx.cla()

    def LoadBoardData(self, File = None):
        self.Data = Storage.Open(File)

        self.Rotation = 0
        self.CH = Circuit.ComponentsHandler(self.Data.Components)
        self.CanHighlight = [None]
        self.Highlighed = None
        self.TmpComponents = []

        self.SetView(self.Data.View)

    def StartComponent(self, CClass):
        self.SelectLibComponent(self.CompToButtonMap[CClass])
        self.Modes.Build()
        self.TmpComponents.append(CClass(self.Cursor, self.Rotation))
        self.Draw()

    def ClearTmpComponent(self):
        while self.TmpComponents:
            self.TmpComponents.pop(0).Clear()

    def OnKeyMove(self, Motion, Mod):
        if self.Modes.Console:
            return
        Move = Motion*10**(int(Mod == 1))
        self.Cursor += Move
        self.OnMove()

    def OnClickMove(self, Click):
        if self.Modes.Console:
            self.Modes.Default()
        self.Cursor = np.rint(Click).astype(int)
        self.OnMove()

    def SetView(self, View = None):
        if View is None:
            Log("Setting default view")
            self.Size = Params.GUI.View.Zooms[0]
            if (self.CH.ComponentsLimits == 0).all():
                self.Size = Params.GUI.View.Zooms[0]
            else:
                self.Size = max(Params.GUI.View.Zooms[0], (self.CH.ComponentsLimits[:,1] - self.CH.ComponentsLimits[:,0]).max())
            self.Cursor = self.CH.ComponentsLimits.mean(axis = 0).astype(int)
            self.LeftBotLoc = self.Cursor - (self.Size // 2)
        else:
            self.Size = np.array(View.Size)
            self.Cursor = np.array(View.Cursor)
            self.LeftBotLoc = np.array(View.LeftBotLoc)
        self.SetBoardLimits()
        
        self.UpdateCursorPlot()
        self.MoveHighlight()
        self.Draw()

    def OnMove(self):
        self.UpdateCursorPlot()
        self.CheckBoardLimits()
        self.MoveHighlight()
        if self.Modes.Build:
            for Component in self.TmpComponents:
                Component.Drag(self.Cursor)
        if self.Modes.Default:
            self.CheckConnexionAvailable()
        self.Draw()

    def NextZoom(self):
        self.DisplayToolbar.children['!checkbutton2'].deselect()
        if self.Size not in Params.GUI.View.Zooms:
            self.Size = Params.GUI.View.Zooms[0]
        else:
            self.Size = Params.GUI.View.Zooms[(Params.GUI.View.Zooms.index(self.Size)+1)%len(Params.GUI.View.Zooms)]
        self.LeftBotLoc = self.Cursor - (self.Size // 2)
        self.SetBoardLimits()
        self.Draw()
        
    def UpdateCursorPlot(self):
        self.Plots['Cursor'].set_data(*self.Cursor)
        if Params.GUI.View.CursorLinesWidth:
            self.Plots['HCursor'].set_data([-Params.Board.Max, Params.Board.Max], [self.Cursor[1], self.Cursor[1]])
            self.Plots['VCursor'].set_data([self.Cursor[0], self.Cursor[0]], [-Params.Board.Max, Params.Board.Max])

    def CheckBoardLimits(self):
        Displacement = np.maximum(0, self.Cursor + Params.GUI.View.DefaultMargin - (self.LeftBotLoc + self.Size))
        if Displacement.any():
            self.LeftBotLoc += Displacement
            self.SetBoardLimits()
        else:
            Displacement = np.maximum(0, self.LeftBotLoc - (self.Cursor - Params.GUI.View.DefaultMargin))
            if Displacement.any():
                self.LeftBotLoc -= Displacement
                self.SetBoardLimits()
    def SetBoardLimits(self):
        self.DisplayAx.set_xlim(self.LeftBotLoc[0],self.LeftBotLoc[0]+self.Size)
        self.DisplayAx.set_ylim(self.LeftBotLoc[1],self.LeftBotLoc[1]+self.Size)

    def SetWireBuildMode(self, mode=None):
        if mode is None:
            mode = 1-self.Library.Wire.BuildMode
        self.WireButtons[mode].configure(background = Colors.GUI.Widget.pressed)
        self.WireButtons[1-mode].configure(background = Colors.GUI.Widget.default)
        self.Library.Wire.BuildMode = mode
        if self.Modes.Build and self.Library.IsWire(self.TmpComponents[0]):
            self.TmpComponents[0].UpdateLocation()
            self.Draw()

    def Set(self):
        Joins = self.CH.HasItem(self.Cursor)
        if self.Modes.Build:
            if self.TmpComponents:
                if self.CH.Register(self.TmpComponents[0]):
                    self.MoveHighlight()
                    PreviousCComp = self.TmpComponents.pop(0).__class__
                    if Params.GUI.Behaviour.AutoContinueComponent and (not self.Library.IsWire(PreviousCComp) or not Params.GUI.Behaviour.StopWireOnJoin or not Joins):
                        self.StartComponent(PreviousCComp)
                    else:
                        self.Modes.Default()
                        self.Draw()
        elif self.Modes.Default:
            if self.CH.Wired(self.Cursor):
                self.StartComponent(self.Library.Wire)

    def Switch(self):
        if self.Modes.Build and self.Library.IsWire(self.TmpComponents[0]):
            self.SetWireBuildMode()
        if self.Modes.Default:
            self.NextHighlight()
            self.DisplayFigure.canvas.draw()

    def Select(self):
        if not self.Modes.Default:
            return
        if not self.Highlighed is None:
            if self.Highlighed not in self.TmpComponents:
                self.TmpComponents.append(self.Highlighed)
                self.Highlighed.Select(True)
            else:
                self.TmpComponents.remove(self.Highlighed)
                self.Highlighed.Select(False)
            self.DisplayFigure.canvas.draw()

    def Rotate(self, var):
        self.Rotation = (self.Rotation + 1) & 0b11
        for Component in self.TmpComponents:
            Component.Rotate()
        if self.TmpComponents:
            self.Draw()

    def MoveHighlight(self):
        self.CanHighlight = [Group for Group in self.CH.CursorGroups(self.Cursor) if len(Group) > 1] + self.CH.CursorComponents(self.Cursor) + self.CH.CursorCasings(self.Cursor) # Single item groups would create odd behaviour
        if not self.CanHighlight:
            self.CanHighlight = [None]
        if self.Highlighed not in self.CanHighlight:
            self.SwitchHighlight(self.CanHighlight[0])
    def NextHighlight(self):
        self.SwitchHighlight(self.CanHighlight[(self.CanHighlight.index(self.Highlighed)+1)%len(self.CanHighlight)])
    def SwitchHighlight(self, Item):
        if Item == self.Highlighed:
            return
        if not self.Highlighed is None:
            self.Highlighed.Highlight(False)
        self.Highlighed = Item
        if not Item is None:
            self.Highlighed.Highlight(True)

    def Draw(self):
        GroupsInfo = self.CH.GroupsInfo(self.Cursor)
        self.MainFrame.Board.DisplayToolbar.Labels.CursorLabel['text'] = f"{self.Cursor.tolist()}" + bool(GroupsInfo)*": " + self.CH.GroupsInfo(self.Cursor)
        self.MainFrame.Board.DisplayToolbar.Labels.CasingLabel['text'] = self.CH.CasingsInfo(self.Cursor)
        self.DisplayFigure.canvas.draw()

    def _ToggleConnexion(self):
        self.CH.ToggleConnexion(self.Cursor)
        self.MoveHighlight()
        self.Draw()
    def CheckConnexionAvailable(self):
        Column = self.CH.Map[self.Cursor[0], self.Cursor[1], :]
        if not Column[-1] and (Column[:-1] != 0).sum() > 3:
            self.MainFrame.Board.Controls.ToggleConnexion.configure(state = Tk.NORMAL)
        else:
            self.MainFrame.Board.Controls.ToggleConnexion.configure(state = Tk.DISABLED)

    def LoadGUI(self):
        self._Icons = {}
    
        self.LoadKeys()

        self.MainFrame = SFrame(self.MainWindow)
        self.MainFrame.AddFrame("TopPanel", 0, 0, columnspan = 3)
        self.MainFrame.AddFrame("Library", 1, 0, Side = Tk.TOP)
        self.MainFrame.AddFrame("Board", 1, 1, Side = Tk.TOP)
        self.MainFrame.AddFrame("RightPanel", 1, 2, Side = Tk.TOP)
        self.MainFrame.AddFrame("Console", 2, 0, columnspan = 3, Side = Tk.LEFT)

        self.LoadMenu()
        self.LoadConsole()
        self.LoadBoard()
        self.LoadRightPanel()
        self.LoadLibraryGUI()

    def Open(self):
        raise NotImplementedError
    def Save(self):
        raise NotImplementedError

    def LoadKeys(self):
        Controls = Params.GUI.Controls
        self.KeysFuctionsDict = {}
        self.MainWindow.bind('<Key>', lambda e: self.ConsoleFilter(self.KeysFuctionsDict.get(e.keysym.lower(), Void), e.keysym.lower(), e.state))

        self.AddControlKey(Controls.Connect, lambda key, mod: self._ToggleConnexion())
        self.AddControlKey(Controls.Close,   lambda key, mod: self.Close(0))
        self.AddControlKey(Controls.Delete,  lambda key, mod: self.Delete())
        self.AddControlKey(Controls.Move,    lambda key, mod: self.Move())
        self.AddControlKey(Controls.Restart, lambda key, mod: self.Close(1))
        self.AddControlKey(Controls.Rotate,  lambda key, mod: self.Rotate(mod))
        self.AddControlKey(Controls.Select,  lambda key, mod: self.Select())
        self.AddControlKey(Controls.Set,     lambda key, mod: self.Set())
        self.AddControlKey(Controls.Switch,  lambda key, mod: self.Switch())
        for Key in Controls.Moves:
            self.AddControlKey(Key, lambda key, mod: self.OnKeyMove(Params.GUI.Controls.Moves[key], mod))
        for Mode in self.Modes.List:
            if Mode.Key is None:
                continue
            self.AddControlKey(Mode.Key, lambda key, mod, Mode = Mode: Mode())

        #self.MainWindow.bind('<Key>', lambda e: print(e.__dict__)) # Override to check key value
    def ConsoleFilter(self, Callback, Symbol, Modifier):
        if self.MainWindow.focus_get() == self.MainFrame.Console.ConsoleInstance.text and not Symbol in ('escape', 'f4', 'f5'): # Hardcoded so far, should be taken from Params as well
            return
        Callback(Symbol, Modifier)

    def AddControlKey(self, Key, Callback):
        if Key in self.KeysFuctionsDict:
            raise ValueError(f"Used key : {Key}")
        self.KeysFuctionsDict[Key] = Callback

    def LoadMenu(self):
        MainMenu = Tk.Menu(self.MainWindow)
        FMenu = Tk.Menu(MainMenu, tearoff=0)
        FMenu.add_command(label="New", command=self.New)
        FMenu.add_command(label="Open", command=self.Open)
        FMenu.add_command(label="Save", command=self.Save)
        FMenu.add_separator()
        FMenu.add_command(label="Exit", command=self.Close)
        MainMenu.add_cascade(label="File", menu=FMenu)

        EMenu = Tk.Menu(MainMenu, tearoff=0)
        EMenu.add_command(label="Undo", command=self.Undo)
        EMenu.add_command(label="Options", command=self.Options)
        MainMenu.add_cascade(label="Edit", menu=EMenu)

        HMenu = Tk.Menu(MainMenu, tearoff=0)
        HMenu.add_command(label="Help Index", command=Void)
        HMenu.add_command(label="About...", command=self.About)
        MainMenu.add_cascade(label="Help", menu=HMenu)

        self.MainWindow.config(menu=MainMenu)

    def New(self):
        raise NotImplementedError
    def Undo(self):
        raise NotImplementedError
    def Options(self):
        raise NotImplementedError
    def About(self):
        raise NotImplementedError

    def LoadConsole(self):
        #self.MainFrame.Console.AddWidget(Console.ConsoleWidget, "Console", _locals=locals(), exit_callback=self.MainWindow.destroy)
        ConsoleInstance = ConsoleWidget(self.MainFrame.Console.frame, locals(), self.MainWindow.destroy)
        ConsoleInstance.pack(fill=Tk.BOTH, expand=True)
        self.MainFrame.Console.RemoveDefaultName()
        self.MainFrame.Console.AdvertiseChild(ConsoleInstance, "ConsoleInstance")
        ConsoleInstance.text.bind('<FocusIn>', lambda e:self.Modes.Console())

    def LoadBoard(self):
        self.MainFrame.Board.AddFrame("Controls", Side = Tk.LEFT)
        self.MainFrame.Board.AddFrame("View")
        self.MainFrame.Board.AddFrame("DisplayToolbar", Side = Tk.LEFT)
        self.LoadControls()
        self.LoadView()
        self.LoadDisplayToolbar()

    def LoadControls(self):
        self._Icons['WSImage'] = Tk.PhotoImage(file="./images/WireStraight.png")
        self.MainFrame.Board.Controls.AddWidget(Tk.Button, "WireStraight", image=self._Icons['WSImage'], height = 30, width = 30, command = lambda:self.SetWireBuildMode(0))
        self._Icons['WDImage'] = Tk.PhotoImage(file="./images/WireDiagonal.png")
        self.MainFrame.Board.Controls.AddWidget(Tk.Button, "WireDiagonal", image=self._Icons['WDImage'], height = 30, width = 30, command = lambda:self.SetWireBuildMode(1))
        self.WireButtons = (self.MainFrame.Board.Controls.WireStraight, self.MainFrame.Board.Controls.WireDiagonal)
        self.SetWireBuildMode(Params.GUI.Behaviour.DefaultWireBuildMode)
        self._Icons['DotImage'] = Tk.PhotoImage(file="./images/Dot.png").subsample(10)
        self.MainFrame.Board.Controls.AddWidget(Tk.Button, "ToggleConnexion", image=self._Icons['DotImage'], height = 30, width = 30, state = Tk.DISABLED, command = lambda:self._ToggleConnexion())

        self.MainFrame.Board.Controls.AddWidget(ttk.Separator, orient = 'vertical')

        self._Icons['RLImage'] = Tk.PhotoImage(file="./images/RotateLeft.png").subsample(8)
        self.MainFrame.Board.Controls.AddWidget(Tk.Button, "RotateLeft", image=self._Icons['RLImage'], height = 30, width = 30, command = lambda:self.Rotate(0))
        self._Icons['RRImage'] = Tk.PhotoImage(file="./images/RotateRight.png").subsample(8)
        self.MainFrame.Board.Controls.AddWidget(Tk.Button, "RotateRight", image=self._Icons['RRImage'], height = 30, width = 30, command = lambda:self.Rotate(1))

    def LoadView(self):
        self.DisplayFigure = matplotlib.figure.Figure(figsize=Params.GUI.View.FigSize, dpi=Params.GUI.View.DPI)
        self.DisplayFigure.subplots_adjust(0., 0., 1., 1.)
        self.DisplayAx = self.DisplayFigure.add_subplot(111)
        self.DisplayAx.set_aspect("equal")
        self.DisplayAx.tick_params('both', left = False, bottom = False, labelleft = False, labelbottom = False)
        self.DisplayAx.set_facecolor((0., 0., 0.))

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

        self.DisplayCanvas = matplotlib.backends.backend_tkagg.FigureCanvasTkAgg(self.DisplayFigure, self.MainFrame.Board.View.frame)
        self.DisplayCanvas.draw()
        self.DisplayCanvas.mpl_connect('button_press_event', lambda e:self.OnClickMove(np.array([e.xdata, e.ydata])))

        self.MainFrame.Board.View.AdvertiseChild(self.DisplayCanvas.get_tk_widget(), "Plot")
        self.MainFrame.Board.View.Plot.grid(row = 0, column = 0)
        self.Library.ComponentBase.Board = self.DisplayAx

    def LoadDisplayToolbar(self):
        self.MainFrame.Board.DisplayToolbar.AddFrame("Buttons", Side = Tk.TOP, Border = False)
        self.MainFrame.Board.DisplayToolbar.AddFrame("Labels", Border = False)
        self.MainFrame.Board.DisplayToolbar.Buttons.RemoveDefaultName()
        self.DisplayToolbar = NavigationToolbar2Tk(self.DisplayCanvas, self.MainFrame.Board.DisplayToolbar.Buttons.frame)
        NewCommands = {'!button':self.SetView, # Remap Home button
                       '!checkbutton2':self.NextZoom # Remap zoom button
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
        self.MainFrame.Board.DisplayToolbar.Labels.AddWidget(Tk.Label, "CasingLabel", row = 1, column = 0, text = "")

    def LoadRightPanel(self):
        pass

    def LoadLibraryGUI(self):
        self.CompToButtonMap = {}
        self.CurrentCompButton = None
        for BookName in self.Library.Books:
            Book = self.Library.__dict__[BookName]
            BookFrame = self.MainFrame.Library.AddFrame(BookName, Side = Tk.TOP, NameDisplayed = True)
            CompFrame = BookFrame.AddFrame("CompFrame", NameDisplayed = False)
            for nComp, CompName in enumerate(Book.Components):
                row = nComp // Params.GUI.Library.Columns
                column = nComp % Params.GUI.Library.Columns
                CompClass = Book.__dict__[CompName]
                Add = ''
                if CompName.lower() in Params.GUI.Controls.Components:
                    Add = f' ({Params.GUI.Controls.Components[CompName.lower()]})'
                    self.AddControlKey(Params.GUI.Controls.Components[CompName.lower()], lambda key, mod, CompClass = CompClass: self.StartComponent(CompClass))
                self.CompToButtonMap[CompClass] = CompFrame.AddWidget(Tk.Button, f"{BookName}.{CompName}", row = row, column = column, text = CompName+Add, height = Params.GUI.Library.ComponentHeight, 
                                                                        command = lambda CompClass = CompClass: self.StartComponent(CompClass))

    def SelectLibComponent(self, Button):
        if Button == self.CurrentCompButton:
            return
        if not self.CurrentCompButton is None:
            self.CurrentCompButton.configure(background = Colors.GUI.Widget.default)
        self.CurrentCompButton = Button
        if not self.CurrentCompButton is None:
            self.CurrentCompButton.configure(background = Colors.GUI.Widget.pressed)

    def Close(self, Restart = False):
        self.MainWindow.quit()
        self.Restart = Restart
        #self.MainWindow.destroy()

def Void(*args, **kwargs):
    pass
    #print(args[0])

class ModeC:
    GUI = None
    Current = None
    ID = None
    Name = None
    Color = None
    def __init__(self):
        self.Key = Params.GUI.Controls.Modes.get(self.ID, None)
        self.Name = Params.GUI.ModesNames[self.ID]
        self.Color = Colors.GUI.Modes[self.ID]
        if self.Current is None:
            ModeC.Current = self
    def __call__(self, Advertise = False):
        if self.Current == self:
            self.__class__.ReloadProps(self.GUI) # This writing allows to make XProps functions like GUI class methods
            return
        if Advertise:
            Log(f"Mode {self.Name}")
        self.GUI.ClearTmpComponent() # If mode changes, we assume that the current component MUST be cleared
        self.Current.__class__.LeaveProps(self.GUI)
        ModeC.Current = self
        self.__class__.SetProps(self.GUI)
        self.GUI.Plots['Cursor'].set_color(self.Color)
        if Params.GUI.View.CursorLinesWidth:
            self.GUI.Plots['HCursor'].set_color(self.Color)
            self.GUI.Plots['VCursor'].set_color(self.Color)
        self.GUI.DisplayFigure.canvas.draw()
    def __bool__(self):
        return self.Current == self

    def SetProps(self):
        pass
    def LeaveProps(self):
        pass
    def ReloadProps(self):
        pass
    @property
    def IsActive(self):
        return self.Current == self

class SFrame:
    def __init__(self, frame, Name="Main", Side = None, NameDisplayed = False):
        self.frame = frame
        self.Name = Name
        self.Children = {}
        self.Side = Side
        self.NameDisplayed = NameDisplayed
        
    def AdvertiseChild(self, NewChild, Name):
        if Name in self.Children:
            raise Exception("Frame name already taken")
        self.Children[Name] = NewChild
        if Name != 'Name':
            self.__dict__[Name] = NewChild

    def AddFrame(self, Name, row=None, column=None, Side = None, Sticky = True, Border = True, NameDisplayed = False, **kwargs):
        self.RemoveDefaultName()

        if Name in self.Children:
            raise Exception("Frame name already taken")
        FrameKwargs = {}
        if Border:
            FrameKwargs["highlightbackground"]="black"
            FrameKwargs["highlightthickness"]=2
        NewFrame = SFrame(Tk.Frame(self.frame, **FrameKwargs), Name, Side = Side, NameDisplayed = NameDisplayed)
        self.Children[Name] = NewFrame
        self.__dict__[Name] = NewFrame

        if self.Side is None:
            if Sticky:
                kwargs["sticky"] = Tk.NSEW
            if row is None or column is None:
                raise Exception(f"Frame {self.Name} must be packed to omit location when adding children")
            NewFrame.frame.grid(row = row, column = column, **kwargs)
        else:
            if Sticky:
                kwargs["fill"] = Tk.BOTH
            NewFrame.frame.pack(side = self.Side, **kwargs)
        NewFrame.AddWidget(Tk.Label, "Name", 0, 0, text = Name)
        return NewFrame

    def RemoveDefaultName(self):
        if "Name" in self.Children and not self.NameDisplayed:
            self.Children["Name"].destroy()
            del self.Children["Name"]

    def AddWidget(self, WidgetClass, Name = "", row=None, column=None, Sticky = True, **kwargs):
        self.RemoveDefaultName()

        if WidgetClass == Tk.Button:
            kwargs['background'] = Colors.GUI.Widget.default
        if Name != "" and Name in self.Children:
            raise Exception("Widget name already taken")
        NewWidget = WidgetClass(self.frame, **kwargs)
        self.Children[Name] = NewWidget
        self.__dict__[Name] = NewWidget
        kwargs = {}
        if self.Side is None:
            if Sticky:
                kwargs["sticky"] = Tk.NSEW
            if row is None or column is None:
                raise Exception(f"Frame {self.Name} must be packed to omit location when adding children")
            NewWidget.grid(row = row, column = column, **kwargs)
        else:
            if Sticky:
                kwargs["fill"] = Tk.BOTH
            NewWidget.pack(side  = self.Side, **kwargs)
        return NewWidget

if __name__ == '__main__':
    G = GUI()
    if G.Restart:
        print("Restarting")
        sys.exit(5)
    else:
        sys.exit(0)

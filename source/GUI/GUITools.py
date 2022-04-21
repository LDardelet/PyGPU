import tkinter as Tk
import numpy as np

import matplotlib
from functools import cached_property
from Console import Log
from Values import Colors, Params, PinDict

ForceReload = True

class ModeC:
    GUI = None
    Current = None
    ID = None
    Name = None
    Color = None
    def __init__(self):
        self.Key = Params.GUI.Controls.Modes.get(self.ID, None)
        self.Color = Colors.GUI.Modes[self.ID]
        if self.Current is None:
            ModeC.Current = self
    def __call__(self, func = None, Message = '', Advertise = False): # Both a call and a wrapper
        if not func is None:
            def ModeWrap(*args, **kwargs):
                if not bool(self) or ForceReload: # Wrapper only changes if necessary
                    self(Message = f'wrap of {func.__name__}')
                func(*args, **kwargs)
            return ModeWrap
        
        if Advertise:
            Log(f"Mode {self.Name}" + bool(Message)*f' ({Message})')
        if self.Current == self:
            self.__class__.ReloadProps(self.GUI) # This writing allows to make XProps functions behave like GUI class methods
            return
        self.Current.__class__.LeaveProps(self.GUI)
        Prev, ModeC.Current = self.Current.__class__, self
        self.__class__.SetProps(self.GUI, Prev)
        self.GUI.UpdateCursorStyle()
    def __bool__(self):
        return self.Current == self
    def SetProps(self, From):
        pass
    def LeaveProps(self):
        pass
    def ReloadProps(self):
        pass
    @property
    def IsActive(self):
        return self.Current == self
    @cached_property
    def Name(self):
        return self.__class__.__name__.split('ModeC')[0]

class DefaultModeC(ModeC):
    ID = 0
    def SetProps(self, From):
        if not From == TextModeC:
            self.ClearTmpComponents()
        self.CheckConnexionToggle()
    def LeaveProps(self):
        self.MainFrame.Board.Controls.ToggleConnexionButton.configure(state = Tk.DISABLED)
    def ReloadProps(self):
        self.ClearTmpComponents()
class TextModeC(ModeC):
    ID = 1
    def SetProps(self, From):
        if self.MainWindow.focus_get() == self.MainWidget:
            self.MainFrame.Console.ConsoleInstance.text.see(Tk.END)
            self.MainFrame.Console.ConsoleInstance.text.focus_set()
    def LeaveProps(self):
        self.MainWidget.focus_set()
class BuildModeC(ModeC):
    ID = 2
    def SetProps(self, From):
        self.ClearTmpComponents()
    def LeaveProps(self):
        self.SetLibraryButtonColor(None)
    def ReloadProps(self):
        self.ClearTmpComponents()
class DeleteModeC(ModeC):
    ID = 3
    def SetProps(self, From):
        if From == BuildModeC:
            self.ClearTmpComponents()
        self.MainFrame.Board.Controls.ToggleConnexionButton.configure(state = Tk.DISABLED)
        self.DeleteSelect()
    def ReloadProps(self):
        self.DeleteConfirm()
class ModesDict:
    Default = DefaultModeC()
    Text    = TextModeC()
    Build   = BuildModeC()
    Delete  = DeleteModeC()
    def __init__(self):
        self.List = (self.Default, self.Text, self.Build, self.Delete)
    @property
    def Current(self):
        return ModeC.Current

class SFrame:
    Prefix = 'C_'
    DefaultLabelName = 'C_DefaultLabelName'
    def __init__(self, frame, Name="Main", Side = None, NameDisplayed = False):
        self.frame = frame
        self.Name = Name
        self.Side = Side
        self.NameDisplayed = NameDisplayed
        
    def AdvertiseChild(self, NewChild, Name):
        if hasattr(self, Name):
            raise Exception(f"Frame name {Name} already taken")
        if Name[:2] != self.Prefix:
            Name = self.Prefix + Name
        setattr(self, Name, NewChild)

    def __getattr__(self, Key):
        if Key[:2] != self.Prefix:
            return getattr(self, self.Prefix+Key)
        raise AttributeError(f"{Key.split(self.Prefix)[-1]} is not an attribute of {self} nor a children name")

    def AddFrame(self, Name, row=None, column=None, Side = None, Sticky = True, Border = True, NameDisplayed = False, NoName = False, Width = None, **kwargs):
        self.RemoveDefaultName()

        FrameKwargs = {}
        if Border:
            FrameKwargs["highlightbackground"]="black"
            FrameKwargs["highlightthickness"]=2
        NewFrame = SFrame(Tk.Frame(self.frame, **FrameKwargs), Name, Side = Side, NameDisplayed = NameDisplayed)
        self.AdvertiseChild(NewFrame, Name)

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
        LabelKwargs = {}
        if not Width is None:
            LabelKwargs['width'] = Width

        NewFrame.AddWidget(Tk.Label, self.DefaultLabelName, 0, 0, text = Name.replace('_', ' ') * (1-NoName), **LabelKwargs)
        return NewFrame

    def Destroy(self, ChildName):
        if ChildName[:2] != self.Prefix:
            ChildName = self.Prefix + ChildName
        Child = getattr(self, ChildName)
        if Child.__class__ == self.__class__:
            for WidgetChild in Child.frame.winfo_children():
                WidgetChild.destroy()
            Child.frame.destroy()
        else:
            Child.destroy()
        delattr(self, ChildName)

    def RemoveDefaultName(self):
        if hasattr(self, self.DefaultLabelName) and not self.NameDisplayed:
            getattr(self, self.DefaultLabelName).destroy()
            delattr(self, self.DefaultLabelName)

    def AddWidget(self, WidgetClass, Name = "", row=None, column=None, Sticky = True, **kwargs):
        self.RemoveDefaultName()

        if WidgetClass == Tk.Button and 'background' not in kwargs:
            kwargs['background'] = Colors.GUI.Widget.default
        NewWidget = WidgetClass(self.frame, **kwargs)
        if Name:
            self.AdvertiseChild(NewWidget, Name)
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

    def __repr__(self):
        return f"SFrame {self.Name}"

class BoardIOWidgetBase:
#    ReturnCallback = None
#    LevelModificationCallback = None
    GUI = None
    Type = None
    DefaultWidgetName = "Widget"
    def __init__(self, Frame, ChildName):
        self.Mask = 0b0
        self.Level = 0
        self.Valid = True
        self._Bits = tuple()
        self.frame = Frame.frame
        if ChildName is None:
            ChildName = self.DefaultWidgetName
        Frame.AdvertiseChild(self, ChildName)

    def Push(self, PreviousBoardLevel):
        return (PreviousBoardLevel & ~self.Mask) | self.MaskedLevel
    def Pull(self, NewBoardLevel, NewBoardValidity):
        Level = 0
        self.Valid = True
        for Bit in reversed(self._Bits):
            Level <<= 1
            Level |= (NewBoardLevel >> Bit) & 0b1 
            if not ((NewBoardValidity >> Bit) & 0b1):
                self.Valid = False
        self.Level = Level
        self.UpdateRepresentation()
    @property
    def Bits(self):
        return self._Bits
    @Bits.setter
    def Bits(self, Bits):
        self._Bits = Bits
        self.Mask = 0b0
        for Bit in Bits:
            self.Mask |= 1<<Bit
        self.OnBitsChange()
        self.UpdateRepresentation()
    @property
    def MaskedLevel(self):
        ML = 0
        L = self.Level
        for Bit in self._Bits:
            ML |= (L & 0b1) << Bit
            L >>= 1
        return ML
    def OnBitsChange(self):
        pass
    def UpdateRepresentation(self):
        pass
    @property
    def NBits(self):
        return len(self._Bits)
    @property
    def MaxLevel(self):
        return (2**self.NBits) - 1

class IntBinHexWidget(BoardIOWidgetBase):
    Name = None
    def __init__(self, TotalWidth):
        self.NameLabel = Tk.Label(self.frame, text = f"{self.Name} ({self.NBits} bits)", width = TotalWidth//3, anchor = Tk.W)
        self.NameLabel.grid(row = 0, column = 0, sticky=Tk.EW)
    @property
    def int(self):
        return str(self.Level)
    def IntSet(self, *args, **kwargs):
        try:
            self.Set(int(self.IntVar.get()))
        except ValueError:
            self.Set(0)
    @property
    def bin(self):
        return format(self.Level, f'#0{2+self.NBits}b')
    def BinSet(self, *args, **kwargs):
        try:
            self.Set(int(self.BinVar.get(), 2))
        except ValueError:
            self.Set(0)
    @property
    def hex(self):
        return format(self.Level, f'#0{2+(self.NBits+3)//4}x')
    def HexSet(self, *args, **kwargs):
        try:
            self.Set(int(self.HexVar.get(), 16))
        except ValueError:
            self.Set(0)
    def OnBitsChange(self):
        self.NameLabel.configure(text = f"{self.Name} ({self.NBits} bits)")

class SEntry(IntBinHexWidget):
    Type = PinDict.Input
    def __init__(self, Frame, Name, Bits, TotalWidth, Group = False, ChildName = None):
        BoardIOWidgetBase.__init__(self, Frame, ChildName)
        
        self.Name = Name
        IntBinHexWidget.__init__(self, TotalWidth)

        self.IntVar = Tk.StringVar(self.frame, self.int)
        self.BinVar = Tk.StringVar(self.frame, self.bin)
        self.HexVar = Tk.StringVar(self.frame, self.hex)
        self.Entries = (Tk.Entry(self.frame, textvariable = self.IntVar, width = TotalWidth//3),
                        Tk.Entry(self.frame, textvariable = self.BinVar, width = TotalWidth//3),
                        Tk.Entry(self.frame, textvariable = self.HexVar, width = TotalWidth//3))
        for nEntry, (Entry, Callback) in enumerate(zip(self.Entries, (self.IntSet, self.BinSet, self.HexSet))):
            Entry.grid(row = 1, column = nEntry)
            Entry.bind("<Return>", Callback)
        self.frame.bind('<FocusOut>', self.Reset)

        self.Bits = Bits

    def Reset(self, *args, **kwargs): # avoid unconfirmed changes to be propagated
        if self.frame.focus_get() != None:
            self.UpdateRepresentation()

    def Set(self, Level):
        if Level > self.MaxLevel:
            self.Level = self.MaxLevel
        else:
            self.Level = Level
        self.GUI.BoardIOWidgetReturnCallback(self)
        self.GUI.BoardIOWidgetLevelModificationCallback(self)

    def UpdateRepresentation(self):
        if self.Valid:
            Color = Colors.GUI.Widget.validEntry
        else:
            Color = Colors.GUI.Widget.wrongEntry
        for (Var, Representation, Entry) in zip((self.IntVar, self.BinVar, self.HexVar), (self.int, self.bin, self.hex), self.Entries):
            Var.set(Representation)
            Entry.configure(fg = Color)

    def __repr__(self):
        return self.Name

class SLabel(IntBinHexWidget):
    Type = PinDict.Output
    def __init__(self, Frame, Name, Bits, TotalWidth, Group = False, ChildName = None):
        BoardIOWidgetBase.__init__(self, Frame, ChildName)

        self.Name = Name
        IntBinHexWidget.__init__(self, TotalWidth)

        self.Labels =  (Tk.Label(self.frame, text=self.int, width = TotalWidth//3, anchor = Tk.W),
                        Tk.Label(self.frame, text=self.bin, width = TotalWidth//3, anchor = Tk.W),
                        Tk.Label(self.frame, text=self.hex, width = TotalWidth//3, anchor = Tk.W))
        for nLabel, Label in enumerate(self.Labels):
            Label.grid(row = 1, column = nLabel)

        self.Bits = Bits

    def UpdateRepresentation(self):
        if self.Valid:
            Color = Colors.GUI.Widget.validLabel
        else:
            Color = Colors.GUI.Widget.wrongLabel
        for (Label, Representation) in zip(self.Labels, (self.int, self.bin, self.hex)):
            Label.configure(text = Representation)
            Label.configure(fg = Color)

    def __repr__(self):
        return self.Name

class SPinEntry(BoardIOWidgetBase):
    def __init__(self, Frame, Pin, ChildName = None):
        BoardIOWidgetBase.__init__(self, Frame, ChildName)
        
        self.Pin = Pin

        self.Type = self.Pin.Type

        self.IndexLabel = Tk.Label(self.frame, text = f"Pin {self.Pin.Index}")
        self.IndexLabel.grid(column = 0, row = 1)

        Tk.Label(self.frame, text = f"Name:").grid(column = 1, row = 0)
        self.NameVar = Tk.StringVar(self.frame, self.Pin.Name)
        self.NameEntry = Tk.Entry(self.frame, textvariable = self.NameVar, width = Params.GUI.RightPanel.PinNameEntryWidth)
        self.NameEntry.grid(column = 1, row = 1)
        self.NameEntry.bind("<Return>", self.SetName)
        self.frame.bind('<FocusOut>', self.ResetName)

        Tk.Label(self.frame, text = f"Group:", width = Params.GUI.RightPanel.PinGroupLabelWidth).grid(column = 2, row = 0)
        self.GroupVar = Tk.StringVar(self.frame, self.Pin.BoardGroup.Name(self.Pin))
#        self.GroupVar.trace_add('write', lambda *args, self=self, **kwargs: self.SetGroup(self.GroupVar.get()))
        self.GroupMenu = Tk.OptionMenu(self.frame, self.GroupVar, *(('',) + PinDict.BoardGroupsNames[self.Type]), command = lambda *args, self=self, **kwargs: self.SetGroup(self.GroupVar.get()))
#        for GroupName in ('',) + PinDict.BoardGroupsNames[self.Type]:
#            self.GroupMenu['menu'].add_command(label=GroupName, command = lambda *args, GroupName=GroupName, self=self, **kwargs:self.SetGroup(GroupName))
        self.GroupMenu.grid(column = 2, row = 1)

        self.SetButton = Tk.Button(self.frame, bg = Colors.Component.Levels[self.Level], activebackground = Colors.Component.Levels[self.Level], command = self.Switch)
        self.SetButton.grid(column = 3, row = 0, rowspan = 2)
        if self.Type == PinDict.Output:
            self.SetButton.configure(state = Tk.DISABLED)
            self.InvalidColor = Colors.GUI.Widget.wrongLabel
            self.CName = "Label"
        else:
            self.InvalidColor = Colors.GUI.Widget.wrongEntry
            self.CName = "Entry"

        self.Bits = (Pin.TypeIndex,)

        self.IndexDecButton = Tk.Button(self.frame, text = "^", command = lambda *args, **kwargs:self.SetIndex(-1))
        self.IndexDecButton.grid(column = 4, row = 0)
        self.IndexIncButton = Tk.Button(self.frame, text = "v", command = lambda *args, **kwargs:self.SetIndex(+1))
        self.IndexIncButton.grid(column = 4, row = 1)

    def OnBitsChange(self):
        self.IndexLabel.configure(text = f"Pin {self.Pin.Index}")

    def Switch(self):
        self.Level = 1 - self.Level
        self.GUI.BoardIOWidgetLevelModificationCallback(self)

    def SetIndex(self, mod):
        self.GUI.BoardIOWidgetIndexModCallback(self, self.Pin.Index + mod) 
    def SetName(self, *args, **kwargs):
        self.Pin.Name = self.NameVar.get()[:Params.GUI.RightPanel.PinNameEntryWidth]
        self.GUI.BoardIOWidgetReturnCallback(self)
    def ResetName(self, *args, **kwargs):
        if self.frame.focus_get() != None and self.NameVar.get() != self.Pin.Name:
            self.NameVar.set(self.Pin.Name)
    def SetGroup(self, BoardGroup):
        if self.Pin.BoardGroup(self.Pin) == BoardGroup:
            return
        self.Pin.BoardGroup.Set(self.Pin, BoardGroup)
        if BoardGroup:
            self.NameEntry.configure(state = Tk.DISABLED)
            self.UpdateNameInGroup()
        else:
            self.NameEntry.configure(state = Tk.NORMAL)
            self.Pin.Name = self.NameVar.get()[:Params.GUI.RightPanel.PinNameEntryWidth]
            self.GroupVar.set('')
        self.GUI.BoardIOWidgetGroupModification()
    def UpdateNameInGroup(self):
        if not self.Pin.BoardGroup(self.Pin):
            return
        self.Pin.Name = self.Pin.BoardGroup.Name(self.Pin)
        self.GroupVar.set(f"{self.Pin.BoardGroup(self.Pin)}({self.Pin.BoardGroup.Index(self.Pin)})")
    def UpdateRepresentation(self):
        if not self.Valid:
            Color = self.InvalidColor
            if self.Type == PinDict.Input:
                self.SetButton.configure(state = Tk.DISABLED)
        else:
            if self.Type == PinDict.Input:
                self.SetButton.configure(state = Tk.NORMAL)
            Color = Colors.Component.Levels[self.Level]
        self.SetButton.configure(bg = Color)
        self.SetButton.configure(activebackground = Color)

    def __repr__(self):
        return f"{str(self.Pin)} {self.CName}"
    
class BoardDisplayC:
    frame = None
    ClickCallback = None

    def __init__(self):
        self.Figure = matplotlib.figure.Figure(figsize=Params.GUI.View.FigSize, dpi=Params.GUI.View.DPI)
        self.Figure.subplots_adjust(0., 0., 1., 1.)
        self.Ax = self.Figure.add_subplot(111)
        self.Ax.set_aspect("equal")
        self.Ax.tick_params('both', left = False, bottom = False, labelleft = False, labelbottom = False)
        self.Ax.set_facecolor((0., 0., 0.))

        self.Canvas = matplotlib.backends.backend_tkagg.FigureCanvasTkAgg(self.Figure, self.frame)
        self.Widget = self.Canvas.get_tk_widget()

        self.Plots = {}
        Color = 'k'
        self.Plots['Cursor'] = self.Ax.plot(0,0, marker = 'o', color = Color)[0]
        if Params.GUI.View.CursorLinesWidth:
            self.Plots['HCursor'] = self.Ax.plot([-Params.Board.Max, Params.Board.Max], [0,0], linewidth = Params.GUI.View.CursorLinesWidth, color = Color, alpha = 0.3)[0]
            self.Plots['VCursor'] = self.Ax.plot([0,0], [-Params.Board.Max, Params.Board.Max], linewidth = Params.GUI.View.CursorLinesWidth, color = Color, alpha = 0.3)[0]
        RLE = Params.GUI.View.RefLineEvery
        if RLE:
            NLines = Params.Board.Size // RLE
            self.Plots['HLines']=[self.Ax.plot([-Params.Board.Max, Params.Board.Max],
                                 [nLine*RLE, nLine*RLE], color = Colors.GUI.default, alpha = 0.2)[0] for nLine in range(-NLines//2+1, NLines//2)]
            self.Plots['VLines']=[self.Ax.plot([nLine*RLE, nLine*RLE],
                                 [-Params.Board.Max, Params.Board.Max], color = Colors.GUI.default, alpha = 0.2)[0] for nLine in range(-NLines//2+1, NLines//2)]

        self.Cursor = None
        self.xSize = None
        self.LowerLeftViewCorner = None

        self.Board = None

    def OnMove(self):
        self.UpdateCursorPlot()
        Displacement = np.maximum(0, self.Cursor + Params.GUI.View.DefaultMargin - (self.LowerLeftViewCorner + self.Size))
        if Displacement.any():
            self.LowerLeftViewCorner += Displacement
            self.SetBoardLimits()
        else:
            Displacement = np.maximum(0, self.LowerLeftViewCorner - (self.Cursor - Params.GUI.View.DefaultMargin))
            if Displacement.any():
                self.LowerLeftViewCorner -= Displacement
                self.SetBoardLimits()

    def SetView(self):
        if self.Board is None or (self.Board.ComponentsHandler.ComponentsLimits == 0).all():
            self.xSize = Params.GUI.View.Zooms[0]
            self.Cursor = np.zeros(2, dtype = int)
        else:
            self.xSize = max(Params.GUI.View.Zooms[0], (self.Board.ComponentsHandler.ComponentsLimits[:,1] - self.Board.ComponentsHandler.ComponentsLimits[:,0]).max())
            self.Cursor = self.Board.ComponentsHandler.ComponentsLimits.mean(axis = 1).astype(int)

        self.LowerLeftViewCorner = self.Cursor - (self.Size / 2)
        self.SetBoardLimits()
        self.UpdateCursorPlot()

    def SetBoardLimits(self):
        self.Ax.set_xlim(self.LowerLeftViewCorner[0],self.LowerLeftViewCorner[0]+self.xSize)
        self.Ax.set_ylim(self.LowerLeftViewCorner[1],self.LowerLeftViewCorner[1]+self.ySize)

    def NextZoom(self):
        if self.xSize not in Params.GUI.View.Zooms:
            self.xSize = Params.GUI.View.Zooms[0]
        else:
            self.xSize = Params.GUI.View.Zooms[(Params.GUI.View.Zooms.index(self.xSize)+1)%len(Params.GUI.View.Zooms)]
        self.LowerLeftViewCorner = self.Cursor - (self.Size / 2)
        self.SetBoardLimits()

    def UpdateCursorPlot(self):
        self.Plots['Cursor'].set_data(*self.Cursor)
        if Params.GUI.View.CursorLinesWidth:
            self.Plots['HCursor'].set_data([-Params.Board.Max, Params.Board.Max], [self.Cursor[1], self.Cursor[1]])
            self.Plots['VCursor'].set_data([self.Cursor[0], self.Cursor[0]], [-Params.Board.Max, Params.Board.Max])
    def UpdateCursorStyle(self, Color):
        self.Plots['Cursor'].set_color(Color)
        if Params.GUI.View.CursorLinesWidth:
            self.Plots['HCursor'].set_color(Color)
            self.Plots['VCursor'].set_color(Color)

    @property
    def Size(self):
        return np.array([1, Params.GUI.View.FigRatio]) * self.xSize
    @property
    def ySize(self):
        return Params.GUI.View.FigRatio * self.xSize


import tkinter as Tk

import matplotlib
from functools import cached_property
from Console import Log
from Values import Colors, Params, PinDict

ForceReload = True

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
        self.Color = Colors.GUI.Modes[self.ID]
        if self.Current is None:
            ModeC.Current = self
    def __call__(self, func = None, Message = '', Advertise = False): # Both a call and a wrapper
        if not func is None:
            def Wrap(*args, **kwargs):
                if not bool(self) or ForceReload: # Wrapper only changes if necessary
                    self(Message = f'wrap of {func.__name__}')
                func(*args, **kwargs)
            return Wrap
        
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
        #if self.MainWindow.focus_get() != self.MainFrame.Console.ConsoleInstance.text:
        if self.MainWindow.focus_get() == self.MainWidget:
            self.MainFrame.Console.ConsoleInstance.text.see(Tk.END)
            self.MainFrame.Console.ConsoleInstance.text.focus_set()
    def LeaveProps(self):
        self.MainWidget.focus_set()
class BuildModeC(ModeC):
    ID = 2
    def SetProps(self, From):
        self.ClearTmpComponents()
        self.Plots['Cursor'].set_alpha(Params.GUI.Cursor.HiddenAlpha)
    def LeaveProps(self):
        self.Plots['Cursor'].set_alpha(Params.GUI.Cursor.DefaultAlpha)
        self.SetLibraryButtonColor(None)
    def ReloadProps(self):
        self.ClearTmpComponents()
class DeleteModeC(ModeC):
    ID = 3
    def SetProps(self, From):
        if From == BuildModeC:
            self.ClearTmpComponents()
        print(From)
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
            raise Exception("Frame name already taken")
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
        return Child

    def RemoveDefaultName(self):
        if hasattr(self, self.DefaultLabelName) and not self.NameDisplayed:
            getattr(self, self.DefaultLabelName).destroy()
            delattr(self, self.DefaultLabelName)

    def AddWidget(self, WidgetClass, Name = "", row=None, column=None, Sticky = True, **kwargs):
        self.RemoveDefaultName()

        if WidgetClass == Tk.Button:
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
    Mask = 0b0
    Level = 0
    Valid = True
    _Bits = tuple()
    DefaultWidgetName = "Wiget"
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
    @property
    def MaskedLevel(self):
        ML = 0
        L = self.Level
        for Bit in self._Bits: # Reversed ?
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

class SEntry(BoardIOWidgetBase):
    def __init__(self, Frame, Name, Bits, TotalWidth, ChildName = None):
        self.frame = Frame.frame
        self.Name = Name
        self.NameLabel = Tk.Label(self.frame, text = f"", width = TotalWidth)
        self.NameLabel.grid(row = 0, column = 0, columnspan = 3, sticky=Tk.EW)
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
        if ChildName is None:
            ChildName = self.DefaultWidgetName
        Frame.AdvertiseChild(self, ChildName)

    def Reset(self, *args, **kwargs): # avoid unconfirmed changes to be propagated
        if self.frame.focus_get() != None:
            self.UpdateRepresentation()

    def OnBitsChange(self):
        self.NameLabel.configure(text = f"{self.Name} ({self.NBits} bits)")
        self.UpdateRepresentation()

    def Set(self, Level):
        if Level > self.MaxLevel:
            self.Level = self.MaxLevel
        else:
            self.Level = Level
        self.GUI.BoardIOWidgetReturnCallback(self)
        self.GUI.BoardIOWidgetLevelModificationCallback(self)

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

class SLabel(BoardIOWidgetBase):
    def __init__(self, Frame, Name, Bits, TotalWidth, ChildName = None):
        self.frame = Frame.frame
        self.Name = Name
        self.NameLabel = Tk.Label(self.frame, text = f"", width = TotalWidth)
        self.NameLabel.grid(row = 0, column = 0, columnspan = 3)
        self.Labels =  (Tk.Label(self.frame, text=self.int, width = TotalWidth//3, anchor = Tk.W),
                        Tk.Label(self.frame, text=self.bin, width = TotalWidth//3, anchor = Tk.W),
                        Tk.Label(self.frame, text=self.hex, width = TotalWidth//3, anchor = Tk.W))
        for nLabel, Label in enumerate(self.Labels):
            Label.grid(row = 1, column = nLabel)

        self.Bits = Bits
        if ChildName is None:
            ChildName = self.DefaultWidgetName
        Frame.AdvertiseChild(self, ChildName)

    def OnBitsChange(self):
        self.NameLabel.configure(text = f"{self.Name} ({self.NBits} bits)")

    @property
    def int(self):
        return str(self.Level)
    @property
    def bin(self):
        return format(self.Level, f'#0{2+self.NBits}b')
    @property
    def hex(self):
        return format(self.Level, f'#0{2+(self.NBits+3)//4}x')
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
        self.frame = Frame.frame
        self.Pin = Pin

        self.Type = self.Pin.Type

        self.IDLabel = Tk.Label(self.frame, text = self.Pin.Label)
        self.IDLabel.grid(column = 0, row = 0)
        self.NameVar = Tk.StringVar(self.frame, self.Pin.Name)
        self.NameEntry = Tk.Entry(self.frame, textvariable = self.NameVar, width = Params.GUI.RightPanel.PinNameEntryWidth)
        self.NameEntry.grid(column = 0, row = 1)
        self.NameEntry.bind("<Return>", self.SetName)
        self.frame.bind('<FocusOut>', self.Reset)

        self.SetButton = Tk.Button(self.frame, bg = Colors.Component.Levels[self.Level], activebackground = Colors.Component.Levels[self.Level], command = self.Switch)
        self.SetButton.grid(column = 1, row = 0, rowspan = 2)
        if self.Type == PinDict.Output:
            self.SetButton.configure(state = Tk.DISABLED)
            self.InvalidColor = Colors.GUI.Widget.wrongLabel
        else:
            self.InvalidColor = Colors.GUI.Widget.wrongEntry

        self.Bits = (Pin.TypeIndex,)

        if ChildName is None:
            ChildName = self.DefaultWidgetName
        Frame.AdvertiseChild(self, ChildName)

    def OnBitsChange(self):
        self.frame.grid(row = self.Pin.TypeIndex+1, column = 0)
        self.IDLabel['text'] = self.Pin.Label

    def Switch(self):
        self.Level = 1 - self.Level
        self.GUI.BoardIOWidgetLevelModificationCallback(self)

    def SetName(self, *args, **kwargs):
        self.Pin.Name = self.NameVar.get()[:Params.GUI.RightPanel.PinNameEntryWidth]
        self.IDLabel['text'] = self.Pin.Label
        self.GUI.BoardIOWidgetReturnCallback(self)
    def Reset(self, *args, **kwargs):
        if self.frame.focus_get() != None and self.NameVar.get() != self.Pin.Name:
            self.NameVar.set(self.Pin.Name)

    def UpdateRepresentation(self):
        if not self.Valid:
            Color = self.InvalidColor
            self.SetButton.configure(state = Tk.DISABLED)
        else:
            self.SetButton.configure(state = Tk.NORMAL)
            Color = Colors.Component.Levels[self.Level]
        self.SetButton.configure(bg = Color)
        self.SetButton.configure(activebackground = Color)

    def __repr__(self):
        return f"{self.Pin.Label} PinEntry"
    
class BoardDisplayC:
    frame = None
    ClickCallback = None

    GUIItems = ('DisplayFigure', 
                'DisplayAx',
                'DisplayCanvas',
                'Plots',
                'xSize',
                'Cursor',
                'LowerLeftViewCorner')
    def __init__(self):
        self.DisplayFigure = matplotlib.figure.Figure(figsize=Params.GUI.View.FigSize, dpi=Params.GUI.View.DPI)
        self.DisplayFigure.subplots_adjust(0., 0., 1., 1.)
        self.DisplayAx = self.DisplayFigure.add_subplot(111)
        self.DisplayAx.set_aspect("equal")
        self.DisplayAx.tick_params('both', left = False, bottom = False, labelleft = False, labelbottom = False)
        self.DisplayAx.set_facecolor((0., 0., 0.))

        self.DisplayCanvas = matplotlib.backends.backend_tkagg.FigureCanvasTkAgg(self.DisplayFigure, self.frame)

        self.Plots = {}
        Color = 'k'
        self.Plots['Cursor'] = self.DisplayAx.plot(0,0, marker = 'o', color = Color)[0]
        if Params.GUI.View.CursorLinesWidth:
            self.Plots['HCursor'] = self.DisplayAx.plot([-Params.Board.Max, Params.Board.Max], [0,0], linewidth = Params.GUI.View.CursorLinesWidth, color = Color, alpha = 0.3)[0]
            self.Plots['VCursor'] = self.DisplayAx.plot([0,0], [-Params.Board.Max, Params.Board.Max], linewidth = Params.GUI.View.CursorLinesWidth, color = Color, alpha = 0.3)[0]
        RLE = Params.GUI.View.RefLineEvery
        if RLE:
            NLines = Params.Board.Size // RLE
            self.Plots['HLines']=[self.DisplayAx.plot([-Params.Board.Max, Params.Board.Max],
                                 [nLine*RLE, nLine*RLE], color = Colors.GUI.default, alpha = 0.2)[0] for nLine in range(-NLines//2+1, NLines//2)]
            self.Plots['VLines']=[self.DisplayAx.plot([nLine*RLE, nLine*RLE],
                                 [-Params.Board.Max, Params.Board.Max], color = Colors.GUI.default, alpha = 0.2)[0] for nLine in range(-NLines//2+1, NLines//2)]

        self.Cursor = None
        self.xSize = None
        self.LowerLeftViewCorner = None

        self.Board = None

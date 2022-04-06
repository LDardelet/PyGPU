import tkinter as Tk

import matplotlib
from functools import cached_property
from Console import Log
from Values import Colors, Params, PinDict

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
                if not bool(self): # Wrapper only changes if necessary
                    self(Message = f'wrap of {func.__name__}')
                func(*args, **kwargs)
            return Wrap
        
        if Advertise:
            Log(f"Mode {self.Name}" + bool(Message)*f' ({Message})')
        if self.Current == self:
            self.__class__.ReloadProps(self.GUI) # This writing allows to make XProps functions like GUI class methods
            return
        self.Current.__class__.LeaveProps(self.GUI)
        Prev, ModeC.Current = self.Current.__class__, self
        self.__class__.SetProps(self.GUI, Prev)
        self.GUI.Plots['Cursor'].set_color(self.Color)
        if Params.GUI.View.CursorLinesWidth:
            self.GUI.Plots['HCursor'].set_color(self.Color)
            self.GUI.Plots['VCursor'].set_color(self.Color)
        self.GUI.DisplayFigure.canvas.draw()
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
        self.DisplayFigure.canvas.draw()
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
        self.ColorLibComponent(None)
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
    ReturnCallback = None
    LevelModificationCallback = None
    Mask = None
    BitStart = None
    def Push(self, PreviousBoardLevel):
        return (PreviousBoardLevel & ~self.Mask) | (self.Level << self.BitStart)
    def Pull(self, NewBoardLevel):
        self.Level = (NewBoardLevel & self.Mask) >> self.BitStart

class SEntry(BoardIOWidgetBase):
    def __init__(self, frame, Name, NBits, BitStart, TotalWidth):
        self._Level = 0
        self._NBits = NBits
        self._BitStart = BitStart
        self.UpdateMask()
        self.MaxLevel = 2**self.NBits

        self.frame = frame
        self.Name = Name
        self.NameLabel = Tk.Label(frame, text = f"{self.Name} ({self._NBits} bits)", width = TotalWidth)
        self.NameLabel.grid(row = 0, column = 0, columnspan = 3, sticky=Tk.EW)
        self.IntVar = Tk.StringVar(frame, self.int)
        self.BinVar = Tk.StringVar(frame, self.bin)
        self.HexVar = Tk.StringVar(frame, self.hex)
        self.Entries = (Tk.Entry(frame, textvariable = self.IntVar, width = TotalWidth//3),
                        Tk.Entry(frame, textvariable = self.BinVar, width = TotalWidth//3),
                        Tk.Entry(frame, textvariable = self.HexVar, width = TotalWidth//3))
        for nEntry, (Entry, Callback) in enumerate(zip(self.Entries, (self.IntSet, self.BinSet, self.HexSet))):
            Entry.grid(row = 1, column = nEntry)
            Entry.bind("<Return>", Callback)
        self.frame.bind('<FocusOut>', self.Reset)

    def Reset(self, *args, **kwargs): # avoid unconfirmed changes to be propagated
        if self.frame.focus_get() != None:
            self.UpdateRepresentations()

    @property
    def NBits(self):
        return self._NBits
    @NBits.setter
    def NBits(self, NBits):
        self._NBits = NBits
        self.UpdateMask()
        self.MaxLevel = 2**self._NBits
        self.NameLabel.configure(text = f"{self.Name} ({self._NBits} bits)")
        self.CheckValidity()
    @property
    def BitStart(self):
        return self._BitStart
    @BitStart.setter
    def BitStart(self, BitStart):
        self._BitStart = BitStart
        self.UpdateMask()
    def UpdateMask(self):
        self.Mask = ((1 << self.NBits) - 1) << self.BitStart

    @property
    def Level(self):
        return self._Level
    @Level.setter
    def Level(self, Level):
        self._Level = Level
        self.UpdateRepresentations()
        self.CheckValidity()
    def UpdateRepresentations(self):
        for (Var, Representation) in zip((self.IntVar, self.BinVar, self.HexVar), (self.int, self.bin, self.hex)):
            if Var.get() != Representation:
                Var.set(Representation)

    @property
    def int(self):
        return str(self._Level)
    def IntSet(self, *args, **kwargs):
        try:
            self.Level = int(self.IntVar.get())
        except ValueError:
            self.Level = 0
        self.ReturnCallback()
        if self.Valid:
            self.LevelModificationCallback()
    @property
    def bin(self):
        return format(self._Level, f'#0{2+self.NBits}b')
    def BinSet(self, *args, **kwargs):
        try:
            self.Level = int(self.BinVar.get(), 2)
        except ValueError:
            self.Level = 0
        self.ReturnCallback()
        if self.Valid:
            self.LevelModificationCallback()
    @property
    def hex(self):
        return format(self._Level, f'#0{2+(self.NBits+3)//4}x')
    def HexSet(self, *args, **kwargs):
        try:
            self.Level = int(self.HexVar.get(), 16)
        except ValueError:
            self.Level = 0
        self.ReturnCallback()
        if self.Valid:
            self.LevelModificationCallback()

    @property
    def Valid(self):
        return self.Level < self.MaxLevel
    def CheckValidity(self):
        if self.Valid:
            Color = Colors.GUI.Widget.validEntry
        else:
            Color = Colors.GUI.Widget.wrongEntry
        for Entry in self.Entries:
            Entry.configure(fg = Color)
    def __repr__(self):
        return self.Name

class SLabel(BoardIOWidgetBase):
    def __init__(self, frame, Name, NBits, BitStart, TotalWidth):
        self._Level = 0
        self._NBits = NBits
        self._BitStart = BitStart
        self.frame = frame
        self.Name = Name
        self.NameLabel = Tk.Label(frame, text = f"{self.Name} ({self._NBits} bits)", width = TotalWidth)
        self.NameLabel.grid(row = 0, column = 0, columnspan = 3)
        self.Labels =  (Tk.Label(frame, text=self.int, width = TotalWidth//3, anchor = Tk.W),
                        Tk.Label(frame, text=self.bin, width = TotalWidth//3, anchor = Tk.W),
                        Tk.Label(frame, text=self.hex, width = TotalWidth//3, anchor = Tk.W))
        for nLabel, Label in enumerate(self.Labels):
            Label.grid(row = 1, column = nLabel)

    @property
    def NBits(self):
        return self._NBits
    @NBits.setter
    def NBits(self, NBits):
        self._NBits = NBits
        self.UpdateMask()
        self.NameLabel.configure(text = f"{self.Name} ({self._NBits} bits)")
    @property
    def BitStart(self):
        return self._BitStart
    @BitStart.setter
    def BitStart(self, BitStart):
        self._BitStart = BitStart
        self.UpdateMask()
    def UpdateMask(self):
        self.Mask = ((1 << self.NBits) - 1) << self.BitStart

    @property
    def Level(self):
        return self._Level
    @Level.setter
    def Level(self, Level):
        self._Level = Level
        for (Label, Representation) in zip(self.Labels, (self.int, self.bin, self.hex)):
            Label.configure(text = Representation)
    @property
    def int(self):
        return str(self._Level)
    @property
    def bin(self):
        return format(self._Level, f'#0{2+self.NBits}b')
    @property
    def hex(self):
        return format(self._Level, f'#0{2+(self.NBits+3)//4}x')

class SPinEntry(BoardIOWidgetBase):
    def __init__(self, frame, Pin):
        self.frame = frame
        self.Pin = Pin

        self._Level = self.Pin.Level
        self.Type = self.Pin.Type

        self.IDLabel = Tk.Label(frame, text = self.Pin.Label)
        self.IDLabel.grid(column = 0, row = 0)
        self.NameVar = Tk.StringVar(frame, self.Pin.Name)
        self.NameEntry = Tk.Entry(frame, textvariable = self.NameVar, width = Params.GUI.RightPanel.PinNameEntryWidth)
        self.NameEntry.grid(column = 0, row = 1)
        self.NameEntry.bind("<Return>", self.SetName)
        self.frame.bind('<FocusOut>', self.Reset)

        self.SetButton = Tk.Button(frame, bg = Colors.Component.Levels[self.Level], activebackground = Colors.Component.Levels[self.Level], command = self.Switch)
        self.SetButton.grid(column = 1, row = 0, rowspan = 2)
        if self.Type == PinDict.Output:
            self.SetButton.configure(state = Tk.DISABLED)

    @property
    def BitStart(self):
        return self.Pin.TypeIndex
    @property
    def Mask(self):
        return 1 << self.BitStart

    @property
    def Level(self):
        return self._Level
    @Level.setter
    def Level(self, Level):
        self._Level = Level
        self.SetButton.configure(bg = Colors.Component.Levels[self.Level])
        self.SetButton.configure(activebackground = Colors.Component.Levels[self.Level])

    def UpdateIndices(self):
        self.frame.grid(row = self.Pin.TypeIndex+1, column = 0)
        self.IDLabel['text'] = self.Pin.Label

    def Switch(self):
        self.Level = 1 - self.Level
        self.LevelModificationCallback()

    def SetName(self, *args, **kwargs):
        self.Pin.Name = self.NameVar.get()[:Params.GUI.RightPanel.PinNameEntryWidth]
        self.IDLabel['text'] = self.Pin.Label
        self.ReturnCallback()
    def Reset(self, *args, **kwargs):
        if self.frame.focus_get() != None and self.NameVar.get() != self.Pin.Name:
            self.NameVar.set(self.Pin.Name)
    def __repr__(self):
        return f"{self.Pin.Label} PinEntry"

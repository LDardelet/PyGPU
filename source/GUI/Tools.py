import tkinter as Tk

import matplotlib
from functools import cached_property
from Console import Log
from Values import Colors, Params

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

    def AddFrame(self, Name, row=None, column=None, Side = None, Sticky = True, Border = True, NameDisplayed = False, NoName = False, **kwargs):
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
        if not NoName:
            NewFrame.AddWidget(Tk.Label, "Name", 0, 0, text = Name.replace('_', ' '))
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

class SEntry:
    EntryReturnCallback = None
    def __init__(self, Frame, Name, NBits, TotalWidth):
        self._Value = 0
        self._NBits = NBits
        self.MaxValue = 2**self.NBits

        self.Frame = Frame
        self.Name = Name
        self.NameLabel = Tk.Label(Frame, text = f"{self.Name} ({self._NBits} bits)", width = TotalWidth)
        self.NameLabel.grid(row = 0, column = 0, columnspan = 3, sticky=Tk.EW)
        self.IntVar = Tk.StringVar(Frame, self.int)
        self.BinVar = Tk.StringVar(Frame, self.bin)
        self.HexVar = Tk.StringVar(Frame, self.hex)
        self.Entries = (Tk.Entry(Frame, textvariable = self.IntVar, width = TotalWidth//3),
                        Tk.Entry(Frame, textvariable = self.BinVar, width = TotalWidth//3),
                        Tk.Entry(Frame, textvariable = self.HexVar, width = TotalWidth//3))
        for nEntry, (Entry, Callback) in enumerate(zip(self.Entries, (self.IntSet, self.BinSet, self.HexSet))):
            Entry.grid(row = 1, column = nEntry)
            Entry.bind("<Return>", Callback)
        self.Frame.bind('<FocusOut>', self.Reset)

    def Reset(self, *args, **kwargs): # avoid unconfirmed changes to be propagated
        if self.Frame.focus_get() != None:
            self.Value = self._Value

    @property
    def NBits(self):
        return self._NBits
    @NBits.setter
    def NBits(self, Value):
        self._NBits = Value
        self.MaxValue = 2**self._NBits
        self.NameLabel.configure(text = f"{self.Name} ({self._NBits} bits)")
        self.CheckValidity()
    @property
    def Valid(self):
        return self.Value < self.MaxValue
    @property
    def Value(self):
        return self._Value
    @Value.setter
    def Value(self, Value):
        self._Value = Value
        for (Var, Value) in zip((self.IntVar, self.BinVar, self.HexVar), (self.int, self.bin, self.hex)):
            if Var.get() != Value:
                Var.set(Value)
        self.CheckValidity()
    @property
    def int(self):
        return str(self._Value)
    def IntSet(self, *args, **kwargs):
        try:
            self.Value = int(self.IntVar.get())
        except ValueError:
            self.Value = 0
        self.EntryReturnCallback()
    @property
    def bin(self):
        return format(self._Value, f'#0{2+self.NBits}b')
    def BinSet(self, *args, **kwargs):
        try:
            self.Value = int(self.BinVar.get(), 2)
        except ValueError:
            self.Value = 0
        self.EntryReturnCallback()
    @property
    def hex(self):
        return format(self._Value, f'#0{2+(self.NBits+3)//4}x')
    def HexSet(self, *args, **kwargs):
        try:
            self.Value = int(self.HexVar.get(), 16)
        except ValueError:
            self.Value = 0
        self.EntryReturnCallback()
    def CheckValidity(self):
        if self.Valid:
            Color = Colors.GUI.Widget.validEntry
        else:
            Color = Colors.GUI.Widget.wrongEntry
        for Entry in self.Entries:
            Entry.configure(fg = Color)

class SLabel:
    def __init__(self, Frame, Name, NBits, TotalWidth):
        self._Value = 0
        self._NBits = NBits
        self.Frame = Frame
        self.Name = Name
        self.NameLabel = Tk.Label(Frame, text = f"{self.Name} ({self._NBits} bits)", width = TotalWidth)
        self.NameLabel.grid(row = 0, column = 0, columnspan = 3)
        self.Labels =  (Tk.Label(Frame, text=self.int, width = TotalWidth//3, anchor = Tk.W),
                        Tk.Label(Frame, text=self.bin, width = TotalWidth//3, anchor = Tk.W),
                        Tk.Label(Frame, text=self.hex, width = TotalWidth//3, anchor = Tk.W))
        for nLabel, Label in enumerate(self.Labels):
            Label.grid(row = 1, column = nLabel)

    @property
    def NBits(self):
        return self._NBits
    @NBits.setter
    def NBits(self, Value):
        self._NBits = Value
        self.NameLabel.configure(text = f"{self.Name} ({self._NBits} bits)")
    @property
    def Value(self):
        return self._Value
    @Value.setter
    def Value(self, Value):
        self._Value = Value
        for (Label, Value) in zip(self.Labels, (self.int, self.bin, self.hex)):
            Label.configure(text = Value)
    @property
    def int(self):
        return str(self._Value)
    @property
    def bin(self):
        return format(self._Value, f'#0{2+self.NBits}b')
    @property
    def hex(self):
        return format(self._Value, f'#0{2+(self.NBits+3)//4}x')

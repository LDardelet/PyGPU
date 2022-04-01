import tkinter as Tk

import matplotlib
from functools import cached_property
from Console import ConsoleWidget, Log
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
    def __call__(self, func = None, Advertise = False): # Both a call and a wrapper
        if not func is None:
            def Wrap(*args, **kwargs):
                if not bool(self): # Wrapper only changes if necessary
                    self()
                func(*args, **kwargs)
            return Wrap
        
        if Advertise:
            Log(f"Mode {self.Name}")
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
        if not From == ConsoleModeC:
            self.ClearTmpComponents()
        self.CheckConnexionToggle()
    def LeaveProps(self):
        self.MainFrame.Board.Controls.ToggleConnexionButton.configure(state = Tk.DISABLED)
    def ReloadProps(self):
        self.ClearTmpComponents()
        self.DisplayFigure.canvas.draw()
class ConsoleModeC(ModeC):
    ID = 1
    def SetProps(self, From):
        self.MainFrame.Console.ConsoleInstance.text.see(Tk.END)
        if self.MainWindow.focus_get() != self.MainFrame.Console.ConsoleInstance.text:
            self.MainFrame.Console.ConsoleInstance.text.focus_set()
    def LeaveProps(self):
        self.MainWindow.focus_set()
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
    Console = ConsoleModeC()
    Build   = BuildModeC()
    Delete  = DeleteModeC()
    def __init__(self):
        self.List = (self.Default, self.Console, self.Build, self.Delete)
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

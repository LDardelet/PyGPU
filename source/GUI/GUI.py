import tkinter as Tk
import os

import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from importlib import reload

matplotlib.use("TkAgg")

class Gui:
    def __init__(self):
        self.MainWindow = Tk.Tk()
        self.MainWindow.title('Logic Gates Simulator')
    
        self.MainFrame = SFrame(self.MainWindow)
        self.MainFrame.AddFrame("Toolbar", 0, 0, columnspan = 3)
        self.MainFrame.AddFrame("Components", 1, 0, Packed = Tk.N)
        self.MainFrame.AddFrame("Board", 1, 1, Packed = Tk.N)
        self.MainFrame.AddFrame("Parameters", 1, 2, Packed = Tk.N)
        self.MainFrame.AddFrame("Console", 2, 0, columnspan = 3)

        self.MainFrame.Components.AddFrame("I/O", Packed = Tk.N, NameDisplayed = True)
        self.MainFrame.Components.AddFrame("Basic Gates", Packed = Tk.N, NameDisplayed = True)
        self.MainFrame.Components.AddFrame("Custom Components", Packed = Tk.N, NameDisplayed = True)

        self.MainFrame.Board.AddFrame("Buttons", Packed = Tk.W)
        self.MainFrame.Board.AddFrame("View")

        self.DisplayFigure = matplotlib.figure.Figure(figsize=(3,3), dpi=100)
        self.DisplayAx = self.DisplayFigure.add_subplot(111)
        self.DisplayAx.set_aspect("equal")
        self.DisplayAx.axis("off")
        DisplayCanvas = matplotlib.backends.backend_tkagg.FigureCanvasTkAgg(self.DisplayFigure, self.MainFrame.Board.View.frame)
        DisplayCanvas.draw()
        self.MainFrame.Board.View.AdvertiseChild(DisplayCanvas.get_tk_widget(), "Plot")
        self.MainFrame.Board.View.Plot.grid(row = 0, column = 0)
        #DisplayCanvas.mpl_connect('button_press_event', self.OnClick)

        self.MainWindow.bind('<Escape>', lambda event: self._on_closing())

        self.MainWindow.mainloop()

    def _on_closing(self):
        self.MainWindow.quit()
        self.MainWindow.destroy()


class SFrame:
    def __init__(self, frame, Name="Main", Packed = None, NameDisplayed = False):
        self.frame = frame
        self.Name = Name
        self.Children = {}
        self.Packed = Packed
        self.NameDisplayed = NameDisplayed
        
    def AdvertiseChild(self, NewChild, Name):
        if Name in self.Children:
            raise Exception("Frame name already taken")
        self.Children[Name] = NewChild
        self.__dict__[Name] = NewChild

    def AddFrame(self, Name, row=None, column=None, Packed = None, Sticky = True, Border = True, NameDisplayed = False, **kwargs):
        if "Name" in self.Children and not self.NameDisplayed:
            self.Children["Name"].destroy()
            del self.Children["Name"]
            del self.__dict__["Name"]

        if Name in self.Children:
            raise Exception("Frame name already taken")
        FrameKwargs = {}
        if Border:
            FrameKwargs["highlightbackground"]="black"
            FrameKwargs["highlightthickness"]=2
        NewFrame = SFrame(Tk.Frame(self.frame, **FrameKwargs), Name, Packed = Packed, NameDisplayed = NameDisplayed)
        self.Children[Name] = NewFrame
        self.__dict__[Name] = NewFrame

        if self.Packed is None:
            if Sticky:
                kwargs["sticky"] = Tk.NSEW
            if row is None or column is None:
                raise Exception(f"Frame {self.Name} must be packed to omit location when adding children")
            NewFrame.frame.grid(row = row, column = column, **kwargs)
        else:
            if Sticky:
                kwargs["fill"] = Tk.BOTH
            NewFrame.frame.pack(anchor = self.Packed, **kwargs)
        NewFrame.AddWidget(Tk.Label, "Name", 0, 0, text = Name)

    def AddWidget(self, WidgetClass, Name, row=None, column=None, **kwargs):
        if "Name" in self.Children and not self.NameDisplayed:
            self.Children.Name.destroy()
            del self.Children["Name"]
            del self.__dict__["Name"]

        if Name in self.Children:
            raise Exception("Widget name already taken")
        NewWidget = WidgetClass(self.frame, **kwargs)
        self.Children[Name] = NewWidget
        self.__dict__[Name] = NewWidget
        if self.Packed is None:
            if row is None or column is None:
                raise Exception(f"Frame {self.Name} must be packed to omit location when adding children")
            NewWidget.grid(row = row, column = column)
        else:
            NewWidget.pack(anchor = self.Packed)
        return NewWidget

G = Gui()

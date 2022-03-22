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

matplotlib.use("TkAgg")

class GUI:
    def __init__(self):
        self.MainWindow = Tk.Tk()
        self.MainWindow.title('Logic Gates Simulator')

        self._Images = {}
    
        self.MainFrame = SFrame(self.MainWindow)
        self.MainFrame.AddFrame("Toolbar", 0, 0, columnspan = 3)
        self.MainFrame.AddFrame("Components", 1, 0, Side = Tk.TOP)
        self.MainFrame.AddFrame("Board", 1, 1, Side = Tk.TOP)
        self.MainFrame.AddFrame("Parameters", 1, 2, Side = Tk.TOP)
        self.MainFrame.AddFrame("Console", 2, 0, columnspan = 3, Side = Tk.LEFT)

        self.MainFrame.Components.AddFrame("I/O", Side = Tk.TOP, NameDisplayed = True)
        self.MainFrame.Components.AddFrame("Basic Gates", Side = Tk.TOP, NameDisplayed = True)
        self.MainFrame.Components.AddFrame("Custom Components", Side = Tk.TOP, NameDisplayed = True)

        self.MainFrame.Board.AddFrame("Controls", Side = Tk.LEFT)
        self.MainFrame.Board.AddFrame("View")
        self.MainFrame.Board.AddFrame("DisplayToolbar", Side = Tk.LEFT)

        self.LoadBoardData()

        self.LoadControls()
        self.LoadView()
        self.LoadDisplayToolbar()
        self.LoadConsole()
        self.SetDefaultView()

        self.DefineKeys()

        self.MainWindow.mainloop()

    def LoadBoardData(self):
        self.Mode = Params.GUI.Modes.Default

        self.ComponentsHandler = Circuit.ComponentsHandler()
        Circuit.Components.ComponentBase.Handler = self.ComponentsHandler

        self.TmpComponents = []

    def SetMode(self, Mode, Advertise = True):
        self.Mode, Change = Mode, (self.Mode != Mode)
        if Advertise and Change:
            Log(f"Mode {Params.GUI.ModesNames[self.Mode]}")
        self.ClearTmpComponent()
        if self.Mode == Params.GUI.Modes.Wire:
            if Params.GUI.Behaviour.AutoStartWire:
                self.StartWire()
            if not Change:
                return
        if self.Mode == Params.GUI.Modes.Console:
            self.MainFrame.Console.ConsoleInstance.text.see(Tk.END)
            if Change:
                self.MainFrame.Console.ConsoleInstance.text.focus_set()
        else:
            self.MainWindow.focus_set()
        if self.Mode == Params.GUI.Modes.Default:
            self.CheckConnexionAvailable()
        else:
            self.MainFrame.Board.Controls.ToggleConnexion.configure(state = Tk.DISABLED)
        self.UpdateModePlot()

    def StartWire(self):
        self.ClearTmpComponent()
        self.TmpComponents.append(Circuit.Components.Wire(self.Cursor))

    def ClearTmpComponent(self):
        while self.TmpComponents:
            self.TmpComponents.pop(0).destroy()

    def UpdateModePlot(self):
        if self.Mode == Params.GUI.Modes.Default or self.Mode == Params.GUI.Modes.Console:
            Color = Colors.Components.default
        else:
            Color = Colors.Components.build
        self.Plots['Cursor'].set_color(Color)
        if Params.GUI.View.CursorLinesWidth:
            self.Plots['HCursor'].set_color(Color)
            self.Plots['VCursor'].set_color(Color)
        self.DisplayFigure.canvas.draw()

    def OnKeyMove(self, Motion, Mod):
        if self.Mode == Params.GUI.Modes.Console:
            return
        Move = Motion*10**(int(Mod == 1))
        self.Cursor += Move
        self.OnMove()

    def OnClickMove(self, Click):
        if self.Mode == Params.GUI.Modes.Console:
            self.SetMode(Params.GUI.Modes.Default, Advertise = False)
        self.Cursor = np.rint(Click).astype(int)
        self.OnMove()

    def OnMove(self):
        self.UpdateCursor()
        self.ComponentsHandler.MoveHighlight(self.Cursor)
        self.CheckBoardLimits()
        for Component in self.TmpComponents:
            Component.Drag(self.Cursor)
        if self.Mode == Params.GUI.Modes.Default:
            self.CheckConnexionAvailable()
        self.DisplayFigure.canvas.draw()

    def CheckConnexionAvailable(self):
        Column = self.ComponentsHandler.Map[self.Cursor[0], self.Cursor[1], :]
        if not Column[-1] and (Column[:-1] != 0).sum() > 3:
            self.MainFrame.Board.Controls.ToggleConnexion.configure(state = Tk.NORMAL)
        else:
            self.MainFrame.Board.Controls.ToggleConnexion.configure(state = Tk.DISABLED)

    def SetDefaultView(self):
        Log("Setting default view")
        self.Margin = 1
        if (self.ComponentsHandler.ComponentsLimits == 0).all():
            self.Size = Params.GUI.View.Zooms[0]
        else:
            self.Size = max(100, (self.ComponentsHandler.ComponentsLimits[:,1] - self.ComponentsHandler.ComponentsLimits[:,0]).max())
        self.Cursor = self.ComponentsHandler.ComponentsLimits.mean(axis = 0).astype(int)
        self.LeftBotLoc = self.Cursor - (self.Size // 2)
        
        self.SetBoardLimits()
        self.UpdateCursor()
        self.DisplayFigure.canvas.draw()
    def NextZoom(self):
        self.DisplayToolbar.children['!checkbutton2'].deselect()
        if self.Size not in Params.GUI.View.Zooms:
            self.Size = Params.GUI.View.Zooms[0]
        else:
            self.Size = Params.GUI.View.Zooms[(Params.GUI.View.Zooms.index(self.Size)+1)%len(Params.GUI.View.Zooms)]
        self.LeftBotLoc = self.Cursor - (self.Size // 2)
        self.SetBoardLimits()
        self.Draw()
        
    def UpdateCursor(self):
        self.Plots['Cursor'].set_data(*self.Cursor)
        if Params.GUI.View.CursorLinesWidth:
            self.Plots['HCursor'].set_data([-Params.Board.Max, Params.Board.Max], [self.Cursor[1], self.Cursor[1]])
            self.Plots['VCursor'].set_data([self.Cursor[0], self.Cursor[0]], [-Params.Board.Max, Params.Board.Max])
        self.MainFrame.Board.DisplayToolbar.Labels.CursorLabel['text'] = f"Cursor : {self.Cursor.tolist()}"
        self.MainFrame.Board.DisplayToolbar.Labels.ComponentLabel['text'] = self.ComponentsHandler.Repr(self.Cursor)

    def CheckBoardLimits(self):
        Displacement = np.maximum(0, self.Cursor + self.Margin - (self.LeftBotLoc + self.Size))
        if Displacement.any():
            self.LeftBotLoc += Displacement
            self.SetBoardLimits()
        else:
            Displacement = np.maximum(0, self.LeftBotLoc - (self.Cursor - self.Margin))
            if Displacement.any():
                self.LeftBotLoc -= Displacement
                self.SetBoardLimits()
    def SetBoardLimits(self):
        self.DisplayAx.set_xlim(self.LeftBotLoc[0],self.LeftBotLoc[0]+self.Size)
        self.DisplayAx.set_ylim(self.LeftBotLoc[1],self.LeftBotLoc[1]+self.Size)

    def DefineKeys(self):
        Controls = Params.GUI.Controls
        self.KeysFuctionsDict = {
            Controls.Close  :lambda key, mod: self.Close(0),
            Controls.Restart:lambda key, mod: self.Close(1),
            Controls.Rotate :lambda key, mod: self.Rotate(mod),
            Controls.Switch :lambda key, mod: self.Switch(),
            Controls.Set    :lambda key, mod: self.Set(),
            Controls.Connect:lambda key, mod: self._ToggleConnexion(),
        }
        for Key in Controls.Moves:
            self.KeysFuctionsDict[Key] = lambda key, mod: self.OnKeyMove(Params.GUI.Controls.Moves[key], mod)
        for Key in Controls.Modes:
            self.KeysFuctionsDict[Key] = lambda key, mod: self.SetMode(Params.GUI.Controls.Modes[key])

        self.MainWindow.bind('<Key>', lambda e: self.ConsoleFilter(self.KeysFuctionsDict.get(e.keysym.lower(), Void), e.keysym.lower(), e.state))
        #self.MainWindow.bind('<Key>', lambda e: print(e.__dict__))

    def ConsoleFilter(self, Callback, Symbol, Modifier):
        if self.MainWindow.focus_get() == self.MainFrame.Console.ConsoleInstance.text and not Symbol in ('escape', 'f4', 'f5'): # Hardcoded so far, should be taken from Params as well
            return
        Callback(Symbol, Modifier)

    def LoadControls(self):
        self._Images['WSImage'] = Tk.PhotoImage(file="./images/WireStraight.png")
        self.MainFrame.Board.Controls.AddWidget(Tk.Button, "WireStraight", image=self._Images['WSImage'], height = 30, width = 30, command = lambda:self.SetWireMode(0))
        self._Images['WDImage'] = Tk.PhotoImage(file="./images/WireDiagonal.png")
        self.MainFrame.Board.Controls.AddWidget(Tk.Button, "WireDiagonal", image=self._Images['WDImage'], height = 30, width = 30, command = lambda:self.SetWireMode(1))
        self.WireButtons = (self.MainFrame.Board.Controls.WireStraight, self.MainFrame.Board.Controls.WireDiagonal)
        self.SetWireMode(0)
        self._Images['DotImage'] = Tk.PhotoImage(file="./images/Dot.png").subsample(10)
        self.MainFrame.Board.Controls.AddWidget(Tk.Button, "ToggleConnexion", image=self._Images['DotImage'], height = 30, width = 30, state = Tk.DISABLED, command = lambda:self._ToggleConnexion())

        self.MainFrame.Board.Controls.AddWidget(ttk.Separator, orient = 'vertical')

        self._Images['RLImage'] = Tk.PhotoImage(file="./images/RotateLeft.png").subsample(8)
        self.MainFrame.Board.Controls.AddWidget(Tk.Button, "RotateLeft", image=self._Images['RLImage'], height = 30, width = 30, command = lambda:self.Rotate(0))
        self._Images['RRImage'] = Tk.PhotoImage(file="./images/RotateRight.png").subsample(8)
        self.MainFrame.Board.Controls.AddWidget(Tk.Button, "RotateRight", image=self._Images['RRImage'], height = 30, width = 30, command = lambda:self.Rotate(1))

    def SetWireMode(self, mode=None):
        if mode is None:
            mode = 1-Circuit.Components.Wire.BuildMode
        self.WireButtons[mode].configure(background = Colors.GUI.pressed)
        self.WireButtons[1-mode].configure(background = Colors.GUI.bg)
        Circuit.Components.Wire.BuildMode = mode
        if self.Mode == Params.GUI.Modes.Wire:
            self.TmpComponents[0].Update()
            self.Draw()

    def Set(self):
        if self.Mode == Params.GUI.Modes.Wire:
            if self.TmpComponents:
                ClosesCircuit = self.ComponentsHandler.HasItem(self.Cursor)
                if self.TmpComponents[0].Fix(True):
                    self.TmpComponents.pop(0)
                    if Params.GUI.Behaviour.AutoContinueWire and not (ClosesCircuit and Params.GUI.Behaviour.StopWireOnJoin):
                        self.StartWire()
                    self.Draw()
            else:
                self.StartWire()
                self.Draw()

    def Switch(self):
        if self.Mode == Params.GUI.Modes.Wire:
            self.SetWireMode()

    def Rotate(self, var):
        for Component in self.TmpComponents:
            Component.Rotate()
        if self.TmpComponents:
            self.Draw()

    def LoadView(self):
        self.DisplayFigure = matplotlib.figure.Figure(figsize=Params.GUI.View.FigSize, dpi=Params.GUI.View.DPI)
        self.DisplayFigure.subplots_adjust(0., 0., 1., 1.)
        self.DisplayAx = self.DisplayFigure.add_subplot(111)
        self.DisplayAx.set_aspect("equal")
        self.DisplayAx.tick_params('both', left = False, bottom = False, labelleft = False, labelbottom = False)
        self.DisplayAx.set_facecolor((0., 0., 0.))

        self.Plots = {}

        self.Plots['Cursor'] = self.DisplayAx.plot(0,0, marker = 'o', color = Colors.Components.default)[0]
        if Params.GUI.View.CursorLinesWidth:
            self.Plots['HCursor'] = self.DisplayAx.plot([-Params.Board.Max, Params.Board.Max], [0,0], linewidth = Params.GUI.View.CursorLinesWidth, color = Colors.Components.default, alpha = 0.3)[0]
            self.Plots['VCursor'] = self.DisplayAx.plot([0,0], [-Params.Board.Max, Params.Board.Max], linewidth = Params.GUI.View.CursorLinesWidth, color = Colors.Components.default, alpha = 0.3)[0]
        RLE = Params.GUI.View.RefLineEvery
        if RLE:
            NLines = Params.Board.Size // RLE
            self.Plots['HLines']=[self.DisplayAx.plot([-Params.Board.Max, Params.Board.Max], 
                                 [nLine*RLE, nLine*RLE], color = Colors.Components.default, alpha = 0.2)[0] for nLine in range(-NLines//2+1, NLines//2)]
            self.Plots['VLines']=[self.DisplayAx.plot([nLine*RLE, nLine*RLE], 
                                 [-Params.Board.Max, Params.Board.Max], color = Colors.Components.default, alpha = 0.2)[0] for nLine in range(-NLines//2+1, NLines//2)]

        self.DisplayCanvas = matplotlib.backends.backend_tkagg.FigureCanvasTkAgg(self.DisplayFigure, self.MainFrame.Board.View.frame)
        self.DisplayCanvas.draw()
        self.DisplayCanvas.mpl_connect('button_press_event', lambda e:self.OnClickMove(np.array([e.xdata, e.ydata])))

        self.MainFrame.Board.View.AdvertiseChild(self.DisplayCanvas.get_tk_widget(), "Plot")
        self.MainFrame.Board.View.Plot.grid(row = 0, column = 0)
        Circuit.Components.ComponentBase.Board = self.DisplayAx

    def Draw(self):
        self.DisplayFigure.canvas.draw()

    def LoadDisplayToolbar(self):
        self.MainFrame.Board.DisplayToolbar.AddFrame("Buttons", Side = Tk.TOP, Border = False)
        self.MainFrame.Board.DisplayToolbar.AddFrame("Labels", Side = Tk.TOP, Border = False)
        self.MainFrame.Board.DisplayToolbar.Buttons.RemoveDefaultName()
        self.DisplayToolbar = NavigationToolbar2Tk(self.DisplayCanvas, self.MainFrame.Board.DisplayToolbar.Buttons.frame)
        NewCommands = {'!button':self.SetDefaultView, # Remap Home button
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
        self.MainFrame.Board.DisplayToolbar.Labels.AddWidget(Tk.Label, "CursorLabel", text = "")
        self.MainFrame.Board.DisplayToolbar.Labels.AddWidget(Tk.Label, "ComponentLabel", text = "")

    def LoadConsole(self):
        #self.MainFrame.Console.AddWidget(Console.ConsoleWidget, "Console", _locals=locals(), exit_callback=self.MainWindow.destroy)
        ConsoleInstance = ConsoleWidget(self.MainFrame.Console.frame, locals(), self.MainWindow.destroy)
        ConsoleInstance.pack(fill=Tk.BOTH, expand=True)
        self.MainFrame.Console.RemoveDefaultName()
        self.MainFrame.Console.AdvertiseChild(ConsoleInstance, "ConsoleInstance")
        ConsoleInstance.text.bind('<Button-1>', lambda e:self.SetMode(Params.GUI.Modes.Console, Advertise = False))

    def _ToggleConnexion(self):
        self.ComponentsHandler.ToggleConnexion(self.Cursor)

    def Close(self, Restart = False):
        self.MainWindow.quit()
        self.Restart = Restart
        #self.MainWindow.destroy()

def Void(*args, **kwargs):
    pass
    #print(args[0])

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

    def RemoveDefaultName(self):
        if "Name" in self.Children and not self.NameDisplayed:
            self.Children["Name"].destroy()
            del self.Children["Name"]

    def AddWidget(self, WidgetClass, Name = "", row=None, column=None, **kwargs):
        self.RemoveDefaultName()

        if Name != "" and Name in self.Children:
            raise Exception("Widget name already taken")
        NewWidget = WidgetClass(self.frame, **kwargs)
        self.Children[Name] = NewWidget
        self.__dict__[Name] = NewWidget
        if self.Side is None:
            if row is None or column is None:
                raise Exception(f"Frame {self.Name} must be packed to omit location when adding children")
            NewWidget.grid(row = row, column = column)
        else:
            NewWidget.pack(side  = self.Side)
        return NewWidget

if __name__ == '__main__':
    G = GUI()
    if G.Restart:
        print("Restarting")
        sys.exit(5)
    else:
        sys.exit(0)

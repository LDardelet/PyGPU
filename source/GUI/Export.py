import tkinter as Tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog
from PIL import Image
import os, sys
import sys
import numpy as np

import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from GUITools import SFrame
from Values import Params, Colors, PinDict
from Board import BoardC
from Library import LibraryC

from Components import CasedComponentC

matplotlib.use("TkAgg")

class ExportGUI:
    def __init__(self, master, Board):
        self.Libraries = os.listdir(Params.GUI.DataAbsPath + Params.GUI.DataSubFolders['Libraries'])

        self.Library = None
        self.Success = False
        self.CurrentComponent = None

        self.ExportWindow = Tk.Toplevel(master)
        self.LoadGUI()
        self.ExportWindow.bind('<FocusOut>', self.OnClose)
        self.ExportWindow.bind('<Escape>', self.OnClose)

        self.LoadComponent(Board)

    def LoadGUI(self):
        self.MainFrame = SFrame(self.ExportWindow)
        self.ExportWindow.title(Params.ExportGUI.Name)

        self.MainFrame.AddFrame("TopPanel", 0, 0, columnspan = 2, Side = Tk.TOP)
        self.MainFrame.AddFrame("View", 1, 0)
        self.MainFrame.AddFrame("Export", 1, 1, Side = Tk.TOP)

        ComponentFrame = self.MainFrame.TopPanel.AddFrame("Component")
        self.CompNameVar = Tk.StringVar(self.ExportWindow, '')
        ComponentFrame.AddWidget(Tk.Label, row = 0, column = 0, text = "Name:", width = 15)
        ComponentFrame.AddWidget(Tk.Entry, row = 0, column = 1, textvariable = self.CompNameVar, width = 30).bind("<Return>", self.OnNamingChange)

        self.CompSymbolVar = Tk.StringVar(self.ExportWindow, "")
        ComponentFrame.AddWidget(Tk.Label, row = 0, column = 2, text = "Symbol:")
        ComponentFrame.AddWidget(Tk.Entry, row = 0, column = 3, textvariable = self.CompSymbolVar, width = 10).bind("<Return>", self.OnNamingChange)

        LibFrame = self.MainFrame.TopPanel.AddFrame("Library")
        self.LibraryVar = Tk.StringVar(self.ExportWindow, "")
        LibFrame.AddWidget(Tk.Label, row = 0, column = 0, text = "Library:", width = 15)
        LibMenu = LibFrame.AddWidget(Tk.OptionMenu, row = 0, column = 1, variable = self.LibraryVar, value = self.LibraryVar.get())
        LibMenu.configure(width = 40)
        for LibName in LibraryC.List():
            LibMenu['menu'].add_command(label=LibName, command = lambda *args, self=self, LibName = LibName, **kwargs:self.SetLibrary(LibName))
        LibMenu['menu'].add_command(label="New", command = self.NewLibrary)

        PL_FD_Frame = self.MainFrame.TopPanel.AddFrame("PinLabels_ForcedDimensions")

        PinLabelsFrame = PL_FD_Frame.AddFrame("PinLabels", row = 0, column = 0, Border = True)
        PinLabelsFrame.AddWidget(Tk.Label, row = 0, column = 0, text = "Pins labeling:")
        self.PinNumVar = Tk.IntVar(self.ExportWindow, 1)
        P = PinLabelsFrame.AddWidget(Tk.Checkbutton, row = 0, column = 1, text = "Number", variable = self.PinNumVar)
        self.PinNumVar.trace_add('write', self.OnLabelRuleChange)
        self.PinNameVar = Tk.IntVar(self.ExportWindow, 1)
        P = PinLabelsFrame.AddWidget(Tk.Checkbutton, row = 0, column = 2, text = "Name", variable = self.PinNameVar)
        self.PinNameVar.trace_add('write', self.OnLabelRuleChange)

        ForcedDimensionsFrame = PL_FD_Frame.AddFrame("ForcedDimensions", row = 0, column = 1, Border = True)
        ForcedDimensionsFrame.AddWidget(Tk.Label, row = 0, column = 0, text = "Width x Height:")
        self.ForcedWidthVar = Tk.StringVar(self.ExportWindow, "auto")
        self.ForcedHeightVar = Tk.StringVar(self.ExportWindow, "autoCenter[0] - Sizes[0]/2")
        self.ForcedWidthEntry = ForcedDimensionsFrame.AddWidget(Tk.Entry, row = 0, column = 1, textvariable = self.ForcedWidthVar, width = 8)
        self.ForcedWidthEntry.bind("<Return>", self.OnDimensionsChange)
        ForcedDimensionsFrame.AddWidget(Tk.Label, row = 0, column = 2, text = "x")
        self.ForcedHeightEntry = ForcedDimensionsFrame.AddWidget(Tk.Entry, row = 0, column = 3, textvariable = self.ForcedHeightVar, width = 8)
        self.ForcedHeightEntry.bind("<Return>", self.OnDimensionsChange)
        
        TruthTableFrame = self.MainFrame.TopPanel.AddFrame("TruthTable")
        TruthTableFrame.AddWidget(Tk.Label, row = 0, column = 0, text = "Truth table:")
        self.TTButton = TruthTableFrame.AddWidget(Tk.Button, row = 0, column = 1, text = "", width = 20, command = self.ComputeTruthTable)

        self.Display = ComponentDisplayC(self.MainFrame.View.frame)
        self.Display.Widget.grid(row = 0, column = 0)

        self.MainFrame.Export.AddWidget(Tk.Button, text = "Export", command = self.Export, width = 20, height = 6, background = Colors.GUI.Widget.validButton)
        self.MainFrame.Export.AddWidget(Tk.Button, text = "Cancel", command = self.OnClose, width = 20, height = 6, background = Colors.GUI.Widget.wrongButton)

    def LoadComponent(self, Board):
        self.Board = Board
        self.ComponentDict = {
            'CName'   : '',
            'Callback': None,
            'UndefRun': False,
            'Board'   : Board,
            'PinLabelRule': 0b11,
            'InputPinsDef':   tuple(),
            'OutputPinsDef':  tuple(),
            'ForceHeight':    None,
            'ForceWidth' :    None,
            'Symbol'     :    '',
        }
        if self.Board.Name:
            self.CompNameVar.set(self.Board.Name)
            self.ComponentDict['CName'] = self.Board.Name

        if Board.TruthTable.UpToDate:
            self.TTButton.configure(text='Up to date')
            self.TTButton.configure(bg=Colors.GUI.Widget.validButton)
            self.TTButton.configure(activebackground=Colors.GUI.Widget.validButton)
        else:
            self.TTButton.configure(text='Compute')
            self.TTButton.configure(bg=Colors.GUI.Widget.default)

        self.LoadWENS()

        self.UpdateComponent()
        self.MinWidth = self.CurrentComponent.VirtualWidth
        self.MinHeight = self.CurrentComponent.VirtualHeight

        self.ForcedWidthVar.set(f'{self.MinWidth}(auto)')
        self.ForcedHeightVar.set(f'{self.MinHeight}(auto)')


    def UpdateComponent(self):
        if not self.CurrentComponent is None:
            self.CurrentComponent.destroy()
        CurrentClass = type(self.ComponentDict['CName'],
                    (CasedComponentC, ),
                    self.ComponentDict)
        CurrentClass.Display = self.Display.Ax
        self.CurrentComponent = CurrentClass(Location = np.zeros(2, dtype  =int), 
                                             Rotation = 0,
                                             Symmetric = False)
        Margin = 2
        MinValues = np.array(self.CurrentComponent.SWCorner)
        MaxValues = np.array(self.CurrentComponent.NECorner)
        
        Sizes = MaxValues - MinValues + 2*Margin
        Center = (MinValues + MaxValues)/2
        if Sizes[0] * Params.ExportGUI.View.FigRatio > Sizes[1]:
            Sizes[1] = Sizes[0] * Params.ExportGUI.View.FigRatio
        else:
            Sizes[0] = Sizes[1] / Params.ExportGUI.View.FigRatio
        self.Display.Ax.set_xlim(Center[0] - Sizes[0]/2, Center[0] + Sizes[0]/2)
        self.Display.Ax.set_ylim(Center[1] - Sizes[1]/2, Center[1] + Sizes[1]/2)
        self.Display.Canvas.draw()

    def LoadWENS(self):
        for ComponentKey, InitialPins, RotBonus in (('InputPinsDef', self.Board.InputPins, 0), ('OutputPinsDef', self.Board.OutputPins, 2)):
            Pins = {Side : [] for Side in PinDict.WENS}
            for Pin in InitialPins:
                Side = [PinDict.W, PinDict.S, PinDict.E, PinDict.N][Pin.Rotation + RotBonus]
                if Side in (PinDict.W, PinDict.E): # W/E
                    Key = -Pin.Location[1]
                else:
                    Key = Pin.Location[0]
                Pins[Side].append((Key, Pin))
            PinsList = []
            Sides = {Side:[Pin for _, Pin in sorted(Pins[Side], key=lambda a:a[0])] for Side in PinDict.WENS} 
            for Pin in InitialPins:
                Side = [PinDict.W, PinDict.S, PinDict.E, PinDict.N][Pin.Rotation + 2*(Pin.Type == PinDict.Output)]
                PinsList += [((Side, Sides[Side].index(Pin)), Pin.Name)]
            print(ComponentKey, PinsList)
            self.ComponentDict[ComponentKey] = tuple(PinsList)

    def SetLibrary(self, LibName):
        self.Library = LibraryC(LibName)
    def NewLibrary(self, *args, **kwargs):
        LibName = simpledialog.askstring("New library", "Enter new library name", parent=self.ExportWindow)
        self.LibraryVar.set(LibName)
        self.Library = LibraryC.New(LibName)

    def OnDimensionsChange(self, *args, **kwargs):
        try:
            Width = int(self.ForcedWidthVar.get())
            if Width < self.MinWidth:
                self.ForcedWidthVar.set(f'{self.MinWidth}(auto)')
                Width = None
        except:
            Width = None
            self.ForcedWidthVar.set(f'{self.MinWidth}(auto)')
        self.ComponentDict['ForceWidth'] = Width
        try:
            Height = int(self.ForcedHeightVar.get())
            if Height < self.MinHeight:
                self.ForcedHeightVar.set(f'{self.MinHeight}(auto)')
                Height = None
        except:
            Height = None
            self.ForcedHeightVar.set(f'{self.MinHeight}(auto)')
        self.ComponentDict['ForceHeight'] = Height
        self.UpdateComponent()

    def OnNamingChange(self, *args, **kwargs):
        self.ComponentDict['CName'] = self.CompNameVar.get()
        self.ComponentDict['Symbol'] = self.CompSymbolVar.get()
        self.UpdateComponent()

    def OnLabelRuleChange(self, *args, **kwargs):
        self.ComponentDict['PinLabelRule'] = bool(self.PinNameVar.get()) << 1 | bool(self.PinNumVar.get())
        self.UpdateComponent()

    def ComputeTruthTable(self):
        if self.Board.TruthTable.UpToDate:
            return
        NBits = self.Board.NBitsInput
        if NBits == 0:
            print("Nothing to compute")
            return
        if NBits > Params.GUI.TruthTable.WarningLimitNBits:
            if not messagebox.askokcancel("Large input", f"Computing truth table for {NBits} bits ({2**NBits} possibilities) ?"):
                return
        self.Board.ComputeTruthTable()
        self.TTButton.configure(text='Up to date')
        self.TTButton.configure(bg=Colors.GUI.Widget.validButton)
        self.TTButton.configure(activebackground=Colors.GUI.Widget.validButton)

    def Export(self, *args, **kwargs):
        if self.Library is None:
            print("No library selected")
            return
        if not self.ComponentDict['CName']:
            print("Missing component name")
            return
        if (self.ComponentDict['PinLabelRule'] == 0b00) and ((len(self.ComponentDict['InputPinsDef']) > 1) or (len(self.ComponentDict['OutputPinsDef']) > 1)):
            print("Cannot remove all pins labeling with multiple inputs or outputs.")
            return
        Warnings = []
        if not self.Board.TruthTable.UpToDate:
            Warnings.append("Missing truth table")
        if not self.ComponentDict['Symbol']:
            Warnings.append("Missing symbol")
        if self.ComponentDict['CName'] in self.Library:
            Warnings.append("Component name already taken")
        if Warnings:
            if not messagebox.askokcancel("Warnings", '\n - '.join(["Some informations seem to be missing:"]+Warnings)):
                return
        self.Library.AddComponent(self.ComponentDict)
        self.Success = True
        self.OnClose()

    def OnClose(self, *args, **kwargs):
        self.ExportWindow.destroy()

class ComponentDisplayC:
    def __init__(self, frame):
        self.frame = frame
        self.Figure = matplotlib.figure.Figure(figsize=Params.ExportGUI.View.FigSize, dpi=Params.ExportGUI.View.DPI)
        self.Figure.subplots_adjust(0., 0., 1., 1.)
        self.Ax = self.Figure.add_subplot(111)
        self.Ax.set_aspect("equal")
        self.Ax.tick_params('both', left = False, bottom = False, labelleft = False, labelbottom = False)
        self.Ax.set_facecolor((0., 0., 0.))

        self.Canvas = matplotlib.backends.backend_tkagg.FigureCanvasTkAgg(self.Figure, self.frame)
        self.Widget = self.Canvas.get_tk_widget()
        
        self.Plots = {}
        Color = 'k'
        RLE = Params.GUI.View.RefLineEvery
        if RLE:
            NLines = Params.Board.Size // RLE
            self.Plots['HLines']=[self.Ax.plot([-Params.Board.Max, Params.Board.Max],
                                 [nLine*RLE, nLine*RLE], color = Colors.GUI.default, alpha = 0.2)[0] for nLine in range(-NLines//2+1, NLines//2)]
            self.Plots['VLines']=[self.Ax.plot([nLine*RLE, nLine*RLE],
                                 [-Params.Board.Max, Params.Board.Max], color = Colors.GUI.default, alpha = 0.2)[0] for nLine in range(-NLines//2+1, NLines//2)]

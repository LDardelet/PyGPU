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

from Tools import SFrame
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

        self.ExportWindow = Tk.Toplevel(master)
        self.LoadGUI()
        self.ExportWindow.bind('<FocusOut>', self.OnClose)

        self.LoadComponent(Board)

    def LoadGUI(self):
        self.MainFrame = SFrame(self.ExportWindow)
        self.ExportWindow.title(Params.ExportGUI.Name)

        self.MainFrame.AddFrame("TopPanel", 0, 0, columnspan = 2, Side = Tk.TOP)
        self.MainFrame.AddFrame("View", 1, 0, Side = Tk.TOP)
        self.MainFrame.AddFrame("Pin_Placement", 1, 1, Side = Tk.TOP)

        ComponentFrame = self.MainFrame.TopPanel.AddFrame("Component")
        self.CompNameVar = Tk.StringVar(self.ExportWindow, "")
        ComponentFrame.AddWidget(Tk.Label, row = 0, column = 0, text = "Name:", width = 15)
        ComponentFrame.AddWidget(Tk.Entry, row = 0, column = 1, textvariable = self.CompNameVar, width = 30)

        self.CompSymbolVar = Tk.StringVar(self.ExportWindow, "")
        ComponentFrame.AddWidget(Tk.Label, row = 0, column = 2, text = "Symbol:")
        ComponentFrame.AddWidget(Tk.Entry, row = 0, column = 3, textvariable = self.CompSymbolVar, width = 10)

        LibFrame = self.MainFrame.TopPanel.AddFrame("Library")
        self.LibraryVar = Tk.StringVar(self.ExportWindow, "")
        LibFrame.AddWidget(Tk.Label, row = 0, column = 0, text = "Library:", width = 15)
        LibMenu = LibFrame.AddWidget(Tk.OptionMenu, row = 0, column = 1, variable = self.LibraryVar, value = self.LibraryVar.get())
        LibMenu.configure(width = 50)
        for LibName in LibraryC.List():
            LibMenu['menu'].add_command(label=LibName, command = lambda *args, self=self, LibName = LibName, **kwargs:self.SetLibrary(LibName))
        LibMenu['menu'].add_command(label="New", command = self.NewLibrary)

        PinLabelsFrame = self.MainFrame.TopPanel.AddFrame("PinLabels")
        PinLabelsFrame.AddWidget(Tk.Label, row = 0, column = 0, text = "Pins labeling:")
        PinNumVar = Tk.IntVar(self.ExportWindow, 1)
        P = PinLabelsFrame.AddWidget(Tk.Checkbutton, row = 0, column = 1, text = "Number", variable = PinNumVar)
        P.var = PinNumVar
        PinNumVar.trace_add('write', self.OnLabelRuleChange)
        PinNameVar = Tk.IntVar(self.ExportWindow, 1)
        P = PinLabelsFrame.AddWidget(Tk.Checkbutton, row = 0, column = 2, text = "Name", variable = PinNameVar)
        P.var = PinNameVar
        PinNameVar.trace_add('write', self.OnLabelRuleChange)
        
        TruthTableFrame = self.MainFrame.TopPanel.AddFrame("TruthTable")
        TruthTableFrame.AddWidget(Tk.Label, row = 0, column = 0, text = "Truth table:")
        self.TTButton = TruthTableFrame.AddWidget(Tk.Button, row = 0, column = 1, text = "", width = 20, command = self.ComputeTruthTable)

    def LoadComponent(self, Board):
        self.Board = Board
        self.ComponentDict = {
            'Name'    : '',
            'Callback': None,
            'UndefRun': None,
            'Board'   : Board,
            'PinLabelRule': 0b11,
            'InputPinsDef':   tuple(),
            'OutputPinsDef':  tuple(),
            'ForceHeight':    None,
            'ForceWidth' :    None,
            'Symbol'     :    '',
        }
        if Board.TruthTable.UpToDate:
            self.TTButton.configure(text='Up to date')
            self.TTButton.configure(bg=Colors.GUI.Widget.validButton)
            self.TTButton.configure(activebackground=Colors.GUI.Widget.validButton)
        else:
            self.TTButton.configure(text='Compute')
            self.TTButton.configure(bg=Colors.GUI.Widget.default)

    def SetLibrary(self, LibName):
        self.Library = LibraryC(LibName)
    def NewLibrary(self, *args, **kwargs):
        LibName = simpledialog.askstring("New library", "Enter new library name", parent=self.ExportWindow)
        self.LibraryVar.set(LibName)
        self.Library = LibraryC.New(LibName)

    def OnLabelRuleChange(self, *args, **kwargs):
        pass

    def ComputeTruthTable(self):
        if self.Board.TruthTable.UpToDate:
            return
        NBits = self.Board.NBitsInput
        if NBits == 0:
            print("Nothing to compute")
            return
        if NBits > Params.GUI.TruthTable.WarningLimitNBits:
            ans = messagebox.askokcancel("Large input", f"Computing truth table for {NBits} bits ({2**NBits} possibilities) ?")
            if not ans:
                return
        self.Board.ComputeTruthTable()
        self.TTButton.configure(text='Up to date')
        self.TTButton.configure(bg=Colors.GUI.Widget.validButton)
        self.TTButton.configure(activebackground=Colors.GUI.Widget.validButton)

    def OnClose(self, *args, **kwargs):
        self.ExportWindow.destroy()

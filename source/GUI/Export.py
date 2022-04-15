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
from Values import Params, PinDict
from Board import BoardC
from Library import LibraryC

matplotlib.use("TkAgg")

class ExportGUI:
    def __init__(self, master, Board):
        self.Libraries = os.listdir(Params.GUI.DataAbsPath + Params.GUI.DataSubFolders['Libraries'])

        self.Library = None
        self.Success = False

        self.MainWindow = Tk.Toplevel(master)
        self.LoadGUI()

    def LoadGUI(self):
        self.MainFrame = SFrame(self.MainWindow)
        self.MainWindow.title(Params.ExportGUI.Name)

        self.MainFrame.AddFrame("Files", 0, 0, columnspan = 2, Side = Tk.TOP)
        self.MainFrame.AddFrame("View", 1, 0, Side = Tk.TOP)
        self.MainFrame.AddFrame("Pin_Placement", 1, 1, Side = Tk.TOP)

        ComponentFrame = self.MainFrame.Files.AddFrame("Component")
        self.CompNameVar = Tk.StringVar(self.MainWindow, "")
        ComponentFrame.AddWidget(Tk.Label, row = 0, column = 0, text = "Name:", width = 15)
        ComponentFrame.AddWidget(Tk.Entry, row = 0, column = 1, textvariable = self.CompNameVar, width = 30)

        self.CompSymbolVar = Tk.StringVar(self.MainWindow, "")
        ComponentFrame.AddWidget(Tk.Label, row = 0, column = 2, text = "Symbol:")
        ComponentFrame.AddWidget(Tk.Entry, row = 0, column = 3, textvariable = self.CompSymbolVar, width = 10)

        LibFrame = self.MainFrame.Files.AddFrame("Library")
        self.LibraryVar = Tk.StringVar(self.MainWindow, "")
        LibFrame.AddWidget(Tk.Label, row = 0, column = 0, text = "Library:", width = 15)
        LibMenu = LibFrame.AddWidget(Tk.OptionMenu, row = 0, column = 1, variable = self.LibraryVar, value = self.LibraryVar.get())
        LibMenu.configure(width = 50)
        for LibName in LibraryC.List():
            LibMenu['menu'].add_command(label=LibName, command = lambda *args, self=self, LibName = LibName, **kwargs:self.SetLibrary(LibName))
        LibMenu['menu'].add_command(label="New", command = self.NewLibrary)

    def SetLibrary(self, LibName):
        self.Library = LibraryC(LibName)
    def NewLibrary(self, *args, **kwargs):
        LibName = simpledialog.askstring("New library", "Enter new library name", parent=self.MainWindow)
        self.LibraryVar.set(LibName)
        self.Library = LibraryC.New(LibName)

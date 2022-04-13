import tkinter as Tk
from tkinter import ttk
from tkinter import messagebox
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

matplotlib.use("TkAgg")

class ExportGUI:
    def __init__(self, master, Board):
        self.Libraries = os.listdir(Params.GUI.DataAbsPath + Params.GUI.DataSubFolders['Libraries'])

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
        LibFrame.AddWidget(Tk.Entry, row = 0, column = 1, textvariable = self.LibraryVar, width = 50)

import numpy as np
import os

class C:
    grey = 'grey'
    lgrey = 'light grey'
    yellow = 'yellow'
    white = 'white'
    green = 'green'
    red = 'red'
    blue = 'blue'
    orange = 'orange'

class Levels:
    Low      = 0
    High     = 1
    Undef    = 2
    Multiple = 3
    Names = {
        Undef:'?',
        Low  :'LOW',
        High :'HIGH',
        Multiple:'?',
    }

class Colors:
    class GUI:
        default = C.grey
        class Widget:
            default = C.lgrey
            pressed = C.grey
        Modes = {
            0:C.white,  # Default
            1:C.white,  # Console
            2:C.yellow, # Building
            3:C.red, # Building
        }
    class Component:
        Modes = {
            0: C.yellow,   # Building
            1: C.white,     # Fixed, undefined.
            2: C.red,       # Being removed
            3: C.white,    # Selected
        }
        Levels = {
            Levels.Undef    : C.white,
            Levels.Low      : C.orange,
            Levels.High     : C.green,
            Levels.Multiple : C.red,
        }

class Params:
    class Board:
        Size = 1000
        ComponentPinLength = 1
        ComponentMinWidth = 3
        ComponentMinHeight = 3
        CasingsOwnPinsBases = False
        GroupDefaultLevel = Levels.Low
        AllowStableRecursiveLoops = True
    class GUI:
        Name = 'Logic Gates Simulator'
        DataFolder = '~/Documents/PyGPUFiles/'
        BoardSaveSubfolder = 'Projects/'
        class Library:
            Columns = 2
            ComponentHeight = 2
        class View:
            FigSize = (7.,7.)
            DPI = 100
            Zooms = (30, 60, 200)

            DefaultMargin = 1
            RefLineEvery = 20
            CursorLinesWidth = 1
        class Cursor:
            Marker = 'o'
            DefaultAlpha = 1.
            HiddenAlpha = 0.4
        class PlotsWidths:
            HighlightFactor = 2.5
            Wire = 1
            Connexion = 4
            Casing = 0.4
            CNameFontsize = 15
        class PlotsStyles:
            Wire = '-'
            Connexion = '8'
            Casing = '-'
            PinNameLevelColored = True
            AlphaSelection = 0.4
        class Controls:
            Moves = {
                "right":np.array([1,0]),
                "left":np.array([-1,0]),
                "up":np.array([0,1]),
                "down":np.array([0,-1])
            }
            Modes = {0:"escape",
                     1:'twosuperior',
                     3:'d',
            }
            Components = {'and': 'a',
                          'or' : 'o',
                          'not': 'n',
                          'high': 'h',
                          'low': 'g',
                          'wire':'w',
            }
            Close = 'f4'
            Connect = 'c'
#            Delete = 'd'
            Move = 'm'
            Restart = 'f5'
            Reload = 'f6'
            Rotate = 'r'
            Select = 's'
            Set = 'space'
            Switch = 't'
            # Modifiers

        class Console:
            Height = 7
            Width = 120
        class Behaviour:
            AutoContinueComponent = True
            StopWireOnJoin = True
            DefaultWireBuildMode = 1
            AskDeleteConfirmation = False

class PinDict:
    W,E,N,S = 'WENS'
    Input = 0
    Output = 1
    PinTypeNames = {0:'Input',
                    1:'Output'}
Params.Board.Size = Params.Board.Size - (Params.Board.Size & 1)
Params.Board.Max = Params.Board.Size // 2
Params.GUI.DataAbsPath = os.path.realpath(os.path.expanduser(Params.GUI.DataFolder))

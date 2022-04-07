import numpy as np
import os

class C:
    black = 'black'
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
        Low  :'-',
        High :'+',
        Multiple:'?',
    }
    Valid = (Low, High)
    Invalid = (Undef, Multiple)

class Colors:
    class GUI:
        default = C.grey
        class Widget:
            default = C.lgrey
            pressed = C.grey
            validEntry = C.black
            wrongEntry = C.red
            validLabel = C.black
            wrongLabel = C.lgrey
        Modes = {
            0:C.white,  # Default
            1:C.white,  # Console
            2:C.yellow, # Building
            3:C.yellow,    # Removing
        }
    class Component:
        Modes = {
            0: C.yellow,    # Building
            1: C.white,     # Fixed, undefined.
            2: C.yellow,       # Being removed
            3: C.white,     # Selected
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
        class RightPanel:
            Width = 80
            PinNameEntryWidth = 5
        class Cursor:
            Marker = 'o'
            DefaultAlpha = 1.
            HiddenAlpha = 0.4
        class PlotsWidths:
            HighlightFactor = 2.5
            Wire = 1
            Pin = 1
            Connexion = 4
            Casing = 0.4
            CNameFontsize = 15
            BoardPinBoxLength = 4
            BoardPinBoxHeight = 1
        class PlotsStyles:
            Wire = '-'
            Pin = '-'
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
            DefaultBoardPinBuildMode = 0
            AskDeleteConfirmation = False
            AutoSwitchBoardPins = False # Disabled for now as it cannot be changed afterwards

_L = Params.GUI.PlotsWidths.BoardPinBoxLength
_H = Params.GUI.PlotsWidths.BoardPinBoxHeight/2

class PinDict:
    W,E,N,S = 'WENS'
    Input = 0
    Output = 1
    PinTypeNames = {0:'Input',
                    1:'Output'}
    BoardPinStaticCorners =  (np.array([[0,0],
                                        [_H, _H], 
                                        [_L, _H], 
                                        [_L, -_H], 
                                        [_H, -_H]]),
                              np.array([[_L, 0],
                                        [_L-_H, -_H], 
                                        [0, -_H], 
                                        [0, _H], 
                                        [_L-_H, _H]]))


Params.Board.Size = Params.Board.Size - (Params.Board.Size & 1)
Params.Board.Max = Params.Board.Size // 2
Params.GUI.DataAbsPath = os.path.realpath(os.path.expanduser(Params.GUI.DataFolder))

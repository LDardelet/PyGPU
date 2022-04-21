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
    Low      = 0b00
    High     = 0b01
    Undef    = 0b10
    Multiple = 0b11
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
            wrongButton = C.red
            validButton = C.green
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
            2: C.yellow,    # Being removed
            3: C.white,     # Selected
            4: C.red        # Removed, color should never appear
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
        Max = None
        GroupDefaultLevel = Levels.Low
        AllowStableRecursiveLoops = True
    class GUI:
        Name = 'Logic Gates Simulator'
        DataFolder = '~/Documents/PyGPUFiles/'
        DataSubFolders = {"Libraries":"Libraries/",
                          "Projects" :"Projects/",}
        DataAbsPath = None
        class Library:
            Columns = 2
            ComponentHeight = 1
            ComponentWidth = 10
        class View:
            FigSize = (7.,6.)
            FigRatio = None
            DPI = 100
            Zooms = (30, 60, 200)

            DefaultMargin = 1
            RefLineEvery = 20
            CursorLinesWidth = 1
        class CenterPanel:
            BoardMenuWidth = 40
        class RightPanel:
            Width = 60
            HalfWidth = 28
            PinNameEntryWidth = 8
            PinGroupLabelWidth = 8
        class Cursor:
            Marker = 'o'
            DefaultAlpha = 1. # Unused right now
            HiddenAlpha = 0.4 # Unused right now
        class PlotsWidths:
            HighlightFactor = 2.5
            Wire = 1
            Connexion = 4
            Casing = 0.4
            CasingPin = 0.4
            BoardPin = 0.4
            CNameFontsize = 15
        class Dimensions:
            BoardPinBoxLength = 4
            BoardPinBoxHeight = 1
            CasingCornerOffset = 0.4
            CasingPinBaseLength = None
            CasingPinBonusLength = 0
            CasingPinTotalLength = None
            CasingPinArrowLength = 0.4
            CasingPinArrowHeight = 0.5
            CasingPinTextOffset = 0.5 
            ComponentMinVirtualWidth = 1
            ComponentMinVirtualHeight = 0
        class PlotsStyles:
            Wire = '-'
            CasingPin = '-'
            Connexion = '8'
            Casing = '-'
            BoardPin = '-'
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
            Move = 'm'
            Restart = 'f5'
            Reload = 'f6'
            Rotate = 'r'
            Select = 's'
            Set = 'space'
            Switch = 't'

        class Console:
            Height = 7
            Width = 120
        class TruthTable:
            WarningLimitNBits = 10
        class Behaviour:
            AutoContinueComponent = True
            StopWireOnJoin = True
            DefaultWireSymmetric = 1
            DefaultWireRotation = 0
            DefaultBoardPinSymmetric = 0
            AskDeleteConfirmation = False
            AutoSwitchBoardPins = False # Disabled for now as it cannot be changed afterwards
    class ExportGUI:
        Name = "Export component"
        class View:
            FigSize = (3.,3.)
            FigRatio = None
            DPI = 100

            DefaultMargin = 5
            RefLineEvery = 20

Params.GUI.View.FigRatio = Params.GUI.View.FigSize[1] / Params.GUI.View.FigSize[0]
Params.ExportGUI.View.FigRatio = Params.ExportGUI.View.FigSize[1] / Params.ExportGUI.View.FigSize[0]
Params.Board.Size = Params.Board.Size - (Params.Board.Size & 1)
Params.Board.Max = Params.Board.Size // 2
Params.GUI.DataAbsPath = os.path.realpath(os.path.expanduser(Params.GUI.DataFolder)) + '/'
Params.GUI.Dimensions.CasingPinBaseLength = 1.-Params.GUI.Dimensions.CasingCornerOffset
Params.GUI.Dimensions.CasingPinTotalLength = Params.GUI.Dimensions.CasingPinBaseLength + Params.GUI.Dimensions.CasingPinBonusLength
if Params.GUI.Dimensions.CasingPinTotalLength == 0:
    Params.GUI.Dimensions.CasingPinTotalLength = 1
    Params.GUI.Dimensions.CasingPinBonusLength = 1

_L = Params.GUI.Dimensions.BoardPinBoxLength
_H = Params.GUI.Dimensions.BoardPinBoxHeight/2
_l = Params.GUI.Dimensions.CasingPinTotalLength
_la = Params.GUI.Dimensions.CasingPinArrowLength
_h = Params.GUI.Dimensions.CasingPinArrowHeight/2

class PinDict:
    WENS = 'WENS'
    W,E,N,S = WENS
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
    CasingPinStaticCorners = (np.array([[0,0],
                                        [-_la, _h], 
                                        [-_la, -_h]]),
                              np.array([[_l, 0],
                                        [_l-_la, -_h], 
                                        [_l-_la, _h]]))
    BoardGroupsNames = {Input: ('A', 'B', 'In'), 
                   Output:('C', 'D', 'Out')}
    NoneBoardGroupName = ''

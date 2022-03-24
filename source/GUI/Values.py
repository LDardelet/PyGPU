import numpy as np

class Colors:
    class Components:
        default = 'grey'
        build = 'yellow'
        fixed = 'white'
        on = 'green'
        off = 'red'
    class GUI:
        bg = 'light grey'
        pressed = 'grey'

class Params:
    class Board:
        Size = 1000
        ComponentPinLength = 1
        ComponentMinWidth = 3
        ComponentMinHeight = 3
    class GUI:
        class Modes:
            Default = 0
            Wire = 1
            Console = 2
            Build = 3
        ModesNames = {0:"Default",
                      1: "Wire",
                      2: "Console",
                      3: "Build",
        }
        class Library:
            ComponentHeight = 2
        class View:
            FigSize = (7.,7.)
            DPI = 100
            Zooms = (50, 100, 200)

            RefLineEvery = 20
            CursorLinesWidth = 1
        class PlotsWidths:
            HighlightFactor = 1.7
            Wire = 1
            Connexion = 4
            Casing = 0.4
            CNameFontsize = 15
        class PlotsStyles:
            Wire = '-'
            Connexion = '8'
            Casing = '-'
        class Controls:
            Moves = {
                "right":np.array([1,0]),
                "left":np.array([-1,0]),
                "up":np.array([0,1]),
                "down":np.array([0,-1])
            }
            Modes = {"escape":0,
#                     'w':1, # Comment to disable wire mode 
                     'twosuperior':2
            }
            Components = {'AND': 'a',
                          'OR' : 'o',
                          'NOT': 'n',
                          'Wire':'w',
            }
            Close = 'f4'
            Restart = 'f5'
            Rotate = 'r'
            Switch = 't'
            Set = 'space'
            Connect = 'c'
        class Console:
            Height = 9
            Width = 120
        class Behaviour:
            AutoStartWire = False
            AutoContinueWire = True
            AutoContinueComponent = True
            StopWireOnJoin = True
            DefaultWireBuildMode = 1

Params.Board.Max = Params.Board.Size // 2

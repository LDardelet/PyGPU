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
        ComponentDefaultWidth = 4
    class GUI:
        class Modes:
            Default = 0
            Wire = 1
            Console = 2
        ModesNames = {0:"Default",
                      1: "Wire",
                      2: "Console"
        }
        class View:
            FigSize = (7.,7.)
            DPI = 100
            Zooms = (100, 200, 50)

            RefLineEvery = 20
            CursorLinesWidth = 1
        class PlotsWidths:
            HighlightFactor = 1.7
            Wire = 1
            Connexion = 6
            Component = 0.6
        class PlotsStyles:
            Wire = '-'
            Connexion = '8'
            Component
        class Controls:
            Moves = {
                "right":np.array([1,0]),
                "left":np.array([-1,0]),
                "up":np.array([0,1]),
                "down":np.array([0,-1])
            }
            Modes = {"escape":0,
                     'w':1,
                     'twosuperior':2
            }
            Close = 'f4'
            Restart = 'f5'
            Rotate = 'r'
            Switch = 'a'
            Set = 'space'
            Connect = 'c'
        class Console:
            Height = 9
            Width = 120
        class Behaviour:
            AutoStartWire = False
            AutoContinueWire = True
            StopWireOnJoin = True
            DefaultBuildMode = 0

Params.Board.Max = Params.Board.Size // 2

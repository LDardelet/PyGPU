import numpy as np

class C:
    grey = 'grey'
    lgrey = 'light grey'
    yellow = 'yellow'
    white = 'white'
    green = 'green'
    red = 'red'

class Colors:
    class GUI:
        default = C.grey
        class Widget:
            default = C.lgrey
            pressed = C.grey
        Modes = {
            0:C.white,
            1:C.white,
            2:C.yellow,
        }
    class Component:
        build = C.yellow
        fixed = C.white
        on = C.green
        off = C.red


class Params:
    class Board:
        Size = 1000
        ComponentPinLength = 1
        ComponentMinWidth = 3
        ComponentMinHeight = 3
    class GUI:
        ModesNames = {0:"Default",
                      1: "Console",
                      2: "Build",
        }
        class Library:
            Columns = 2
            ComponentHeight = 2
        class View:
            FigSize = (7.,7.)
            DPI = 100
            Zooms = (50, 100, 200)

            RefLineEvery = 20
            CursorLinesWidth = 1
        class Cursor:
            Marker = 'o'
            DefaultAlpha = 1.
            HiddenAlpha = 0.4
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
            Modes = {0:"escape",
                    1:'twosuperior'
            }
            Components = {'and': 'a',
                          'or' : 'o',
                          'not': 'n',
                          'true': 'p',
                          'false': 'm',
                          'wire':'w',
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
            AutoContinueComponent = True
            StopWireOnJoin = True
            DefaultWireBuildMode = 1

Params.Board.Max = Params.Board.Size // 2

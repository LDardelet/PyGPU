import numpy as np

class Colors:
    class Components:
        default = 'grey'
        build = 'yellow'
        fixed = 'white'
    class GUI:
        bg = 'light grey'
        pressed = 'grey'

class Params:
    class Board:
        Size = 1000
    class Wire:
        Width = 1
        DefaultBuildMode = 0
    class GUI:
        class Plots:
            FigSize = (7.,7.)
            DPI = 100
            Zooms = (100, 200, 50)

            RefLineEvery = 20
        class Controls:
            Moves = {
                "right":np.array([1,0]),
                "left":np.array([-1,0]),
                "up":np.array([0,1]),
                "down":np.array([0,-1])
            }
            Modes = {"escape":0,
                'w':1
            }
            Close = 'f4'
            Restart = 'f5'
            Rotate = 'r'
            Switch = 'a'
            Set = 'space'

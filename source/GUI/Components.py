import numpy as np
import matplotlib.pyplot as plt

class ComponentBase:
    Board = None
    def __init__(self, Location):
        self.Location = Location
        self.Highlight = False
        self.Fixed = False



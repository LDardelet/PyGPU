import numpy as np

def Open(File):
    return SaveC(File)

class SaveC:
    def __init__(self, Filename):
        self.Filename = Filename
        if Filename is None:
            self.View = None
            self.Components = None
        else:
            with open(Filename, 'r') as f:
                self.Load(f)
                

    def Save(self, Handler, View):
        pass


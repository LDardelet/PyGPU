from Circuit import ComponentsHandlerC
from Storage import FileHandlerC

class BoardC:
    NewFilename = "Untitled"
    def __init__(self, Filename = None, ParentBoard = None, Display = None):
        self.FileHandler = FileHandlerC()
        self.Filename = Filename

        self.ParentBoard = ParentBoard
        self.OpenBoards = []

        self.Display = Display
        self.Display.Board = self

        if self.Filed:
            self.FileHandler.Load(self.Filename)
            self.ComponentsHandler = self.FileHandler['handler']
        else:
            self.ComponentsHandler = ComponentsHandlerC()

    def Save(self, Filename):
        if not self.ParentBoard is None:
            raise Exception("Cannot save a board opened as componente")
        self.Filename = Filename
        self.FileHandler.Save(Filename, handler = self.ComponentsHandlerC)

    @property
    def Name(self):
        if self.Filed:
            BoardName = self.Filename.split('/')[-1]
        else:
            BoardName = self.NewFilename
        return BoardName

    @property
    def Filed(self):
        return not self.Filename is None

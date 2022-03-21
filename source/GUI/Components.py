import numpy as np
import matplotlib.pyplot as plt

from importlib import reload
from Values import Colors, Markers, Params

class ComponentBase:
    Board = None
    Handler = None
    def __init__(self, Location):
        self.CName = None

        self.Location = np.array(Location)
        self.Rotation = 0
        self.Highlight = False
        self.Fixed = False
        self.Plots = []

        self.AdvertisedLocations = set()
        self.Links = set()

        self.ID = None

    def plot(self, *args, **kwargs):
        self.Plots += self.Board.plot(*args, **kwargs)

    def Highlight(self, var):
        if var == self.Highlight:
            return
        self.Highlight = var
        if self.Highlight:
            for Plot in self.Plots:
                Plot.set_linewidth(Plot.get_linewidth()*2)
        else:
            for Plot in self.Plots:
                Plot.set_linewidth(Plot.get_linewidth()/2)

    def Fix(self, var):
        if var == self.Fixed:
            return
        self.Fixed = var
        if self.Fixed:
            for Plot in self.Plots:
                Plot.set_color(Colors.Components.fixed)
        else:
            for Plot in self.Plots:
                Plot.set_color(Colors.Components.build)

    def LinkedTo(self, ID):
        return ID in self.Links

    def Drag(self, Cursor):
        pass

    def Rotate(self):
        self.Rotation += 1
        self.Update()

    @property
    def Extent(self):
        pass

    def destroy(self):
        for plot in self.Plots:
            plot.remove()

    def __repr__(self):
        return f"{self.__class__.__name__} at {self.Location}"

class Wire(ComponentBase):
    Params = Params.Wire
    BuildMode = Params.DefaultBuildMode
    CName = "Wire"
    def __init__(self, StartLocation, EndLocation = None):
        ComponentBase.__init__(self, StartLocation)

        self.Points = np.zeros((3,2), dtype = int)
        self.plot(self.Points[:2,0], self.Points[:2,1], color = Colors.Components.build, linewidth = self.Params.Width)
        self.plot(self.Points[1:,0], self.Points[1:,1], color = Colors.Components.build, linewidth = self.Params.Width)
        self.Points[0,:] = StartLocation
        if EndLocation is None:
            self.Points[2,:] = StartLocation
        else:
            self.Points[2,:] = EndLocation
        self.Update()

        self.Value = None
        self.Connects = set()

    def Fix(self, var):
        if var:
            RequestedLocations = []
            P1, P2, P3 = self.Points
            (A1, A2), (D1, D2) = self.Angles
            if (P2 != P1).any():
                RequestedLocations.append((P1[0], P1[1], A1+D1))
                for x, y in np.linspace(P1, P2, abs(P2-P1).max()+1, dtype = int)[1:-1]:
                    RequestedLocations.append((x,y,A1))
                    RequestedLocations.append((x,y,A1+4))
                RequestedLocations.append((P2[0], P2[1], (A1+D1+4)%8))
            if (P3 != P2).any():
                RequestedLocations.append((P2[0], P2[1], A2+D2))
                for x, y in np.linspace(P2, P3, abs(P3-P2).max()+1, dtype = int)[1:-1]:
                    RequestedLocations.append((x,y,A2))
                    RequestedLocations.append((x,y,A2+4))
                RequestedLocations.append((P3[0], P3[1], (A2+D2+4)%8))

            if self.Handler.Register(np.array(RequestedLocations), self, (self.Points[0,:2], self.Points[2,:2])):
                ComponentBase.Fix(self, True)
                return True
            else:
                return False

    def Update(self):
        if self.BuildMode == 0: # Straight wires
            if (self.Rotation & 0b1) == 0:
                self.Points[1,0] = self.Points[2,0]
                self.Points[1,1] = self.Points[0,1]
            else:
                self.Points[1,0] = self.Points[0,0]
                self.Points[1,1] = self.Points[2,1]
        else:
            Offsets = self.Points[2,:] - self.Points[0,:]
            Lengths = abs(Offsets)
            StraightAxis = Lengths.argmax()
            SignStraight = np.sign(Offsets[StraightAxis])
            Offsets[1-StraightAxis] = 0
            Offsets[StraightAxis] -= SignStraight * Lengths.min()
            if (self.Rotation & 0b1) == 0:
                self.Points[1,:] = self.Points[0,:] + Offsets
            else:
                self.Points[1,:] = self.Points[2,:] - Offsets
        self.Plots[0].set_data(self.Points[:2,0], self.Points[:2,1])
        self.Plots[1].set_data(self.Points[1:,0], self.Points[1:,1])

    @property
    def Angles(self):
        Offsets = self.Points[1:,:] - self.Points[:2,:]
        As = np.zeros(2, dtype = int)
        Ds = np.zeros(2, dtype = int)
        for i in range(2):
            Offset = Offsets[i, :]
            if Offset[1] == 0:
                As[i] = 0
            elif Offset[0] == Offset[1]:
                As[i] = 1
            elif Offset[0] == 0:
                As[i] = 2
            else:
                As[i] = 3
            if Offset[1] < 0 or (Offset[1] == 0 and Offset[0] < 0):
                Ds[i] = 4
        return As, Ds

    def Drag(self, Cursor):
        self.Points[2,:] = Cursor
        self.Update()

class Connexion(ComponentBase):
    CName = "Connexion"
    def __init__(self, Location, Column): # Warning : 0 is stored in sets, to avoid many checks.
        ComponentBase.__init__(self, Location)
        self.Fixed = True

        self.IDs = set(Column[:8]) # Set to avoid unnecessary storage
        self.NWires = (Column[:8] > 0).sum()
        
        self.plot(self.Location[0], self.Location[1], marker = Markers.Connexion, color = Colors.Components.fixed)
        self.CheckDisplay()

    def Update(self, Column):
        self.IDs = set(Column[:8])
        self.NWires = (Column[:8] > 0).sum()
        self.CheckDisplay()

    def CheckDisplay(self):
        if self.NWires >= 3:
            self.Plots[0].set_alpha(1.)
        else:
            self.Plots[0].set_alpha(0.)

    @property
    def Displayed(self):
        return self.NWires >= 3

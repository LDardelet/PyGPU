import numpy as np
import matplotlib.pyplot as plt

from importlib import reload
from Values import Colors, Params
from Console import Log, LogSuccess, LogWarning, LogError

class ComponentBase:
    Board = None
    Handler = None
    DefaultLinewidth = 0
    DefaultMarkersize = 0
    RotationAllowed = True
    CName = None
    def __init__(self, Location):
        self.Location = np.array(Location)
        self.Rotation = 0
        self.Highlighted = False
        self.Fixed = False
        self.Plots = []
        self.HighlightPlots = []

        self.AdvertisedLocations = set()
        self.Links = set()

        self.ID = None
        self.Group = None

    def plot(self, *args, Highlight = True, **kwargs):
        self.Plots.append(self.Board.plot(*args, **kwargs))
        if Highlight:
            self.HighlightPlots.append(self.Plots[-1])
    def text(self, *args, Highlight = True, **kwargs):
        self.Plots.append(self.Board.text(*args, **kwargs))

    def Highlight(self, var):
        if var == self.Highlighted:
            return
        self.Highlighted = var
        if self.Highlighted:
            Factor = Params.GUI.PlotsWidths.HighlightFactor
        else:
            Factor = 1
        for Plot in self.HighlightPlots:
            Plot.set_linewidth(self.DefaultLinewidth*Factor)
            Plot.set_markersize(self.DefaultMarkersize*Factor)

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
        if not self.RotationAllowed:
            return
        self.Rotation += 1
        self.UpdateLocation()

    @property
    def Extent(self):
        return (self.AdvertisedLocations[:,0].min(), self.AdvertisedLocations[:,1].min(), self.AdvertisedLocations[:,0].max(), self.AdvertisedLocations[:,1].max())

    def destroy(self):
        for plot in self.Plots:
            plot.remove()

    def __repr__(self):
        return f"{self.__class__.__name__} at {self.Location}"

class ComponentPin(ComponentBase):
    DefaultLinewidth = Params.GUI.PlotsWidths.Wire
    DefaultMarkersize = 0
    CName = "Input"
    def __init__(self, Parent, PinBaseOffset, Side, Name = ''):
        self.Parent = Parent
        self.Name = Name
        self.BaseRotation = {'E':0,
                             'N':1,
                             'W':2,
                             'S':3}[Side]
        self.PinBaseOffset = np.array(PinBaseOffset)
        self.Vector = Params.Board.ComponentPinLength * RotateOffset(np.array([1, 0]), self.BaseRotation + 2)
        self.Offset = Self.PinBaseOffset + self.Vector

        Loc = self.Location
        BLoc = self.PinBaseLocation

        self.plot([Loc[0], BLoc[0]], [Loc[1], BLoc[1]], color = Colors.Components.build, linestyle = Params.GUI.PlotsStyles.Wire, linewidth = self.DefaultLinewidth)
        if self.Name:
            self.text(*self.TextLocation, s=self.Name, color = Colors.Components.build, **self.NameTextDict(self.Rotation))

    def UpdateLocation(self):
        Loc = self.Location
        BLoc = self.PinBaseLocation
        self.Plots[0].set_data([Loc[0], BLoc[0]], [Loc[1], BLoc[1]])
        if self.Name:
            TLoc = self.TextLocation
            self.Plots[1].set_x(TLoc[0])
            self.Plots[1].set_y(TLoc[1])
            self.Plots[1].set(self.NameTextDict(self.Rotation))

    @property
    def Location(self):
        return Parent.Location + RotateOffset(self.Offset, self.Rotation)
    @property
    def PinBaseLocation(self):
        return Parent.Location + RotateOffset(self.PinBaseOffset, self.Rotation)
    @property
    def TextLocation(self):
        return Parent.Location + RotateOffset(self.PinBaseOffset - self.Vector, self.Rotation)

    @property
    def Rotation(self):
        return self.Parent.Rotation + self.BaseRotation # Entries are on the left side, so entry wire goes towawrd the right, thus same orientation as its parent
    @property
    def ID(self):
        return Parent.ID
    @property
    def AdvertisedLocations(self):
        Locations = np.zeros((9,3), dtype = int)
        Locations[0,:2] = self.Location
        Locations[0,-1] = (self.Rotation%4)*2
        Locations[1:,:2] = self.PinBaseLocation
        Locations[1:,:] = np.arange(8)
        return Locations

    @staticmethod
    def NameTextDict(Rotation):
        SideIndex = Rotation & 0b11
        return {'rotation':('horizontal', 'vertical', 'horizontal', 'vertical')[SideIndex],
                'va':('center', 'top', 'center', 'bottom')[SideIndex],
                'ha':('right', 'center', 'left', 'center')[SideIndex]}

class Component(ComponentBase): # Template to create any type of component
    DefaultLinewidth = Params.GUI.PlotsWidths.Component
    def __init__(self, Location, Name, West, East, North=None, South=None, ForceWidth = None, ForceHeight = None):
        ComponentBase.__init__(self, Location)
        self.CName = CName

        self.West = West
        self.East = East
        if North is None:
            self.North = []
        else:
            self.North = North
        if South is None:
            self.South = []
        else:
            self.South = South
        self.Width = max(Params.Board.ComponentDefaultWidth, 1+max(len(self.North), len(self.South)))
        self.Height = 1+max(len(self.West), len(self.East))
        if ForceWidth:
            if self.Width > ForceWidth:
                LogError(f"Unable to place all pins on component {self.CName} with constrained width {ForceWidth}")
                raise ValueError
            self.Width = ForceWidth
        if ForceHeight:
            if self.Height > ForceHeight:
                LogError(f"Unable to place all pins on component {self.CName} with constrained height {ForceHeight}")
                raise ValueError
            self.Height = ForceHeight

        self.LocToSWOffset = -np.array([self.Width//2, self.Height//2])

        for Xs, Ys in self.CasingSides:
            self.plot(*Xs, *Ys, color = Colors.Components.build, linestyle = Params.GUI.PlotsStyles.Component, linewidth = self.DefaultLinewidth)

        self.text(*self.Location, s = self.CName, color = Colors.Components.build, va = 'center', ha = 'center', rotation = ('vertical', 'horizontal')[self.Width > 10])

        self.Pins = {}
        for nPin, PinName in enumerate(West):
            Offset = self.LocToSWOffset + self.Height + np.array([0, -nPin-1])
            self.Pins[f"W.{nPin}"] = ComponentPin(self, Offset, 'W', PinName)
        for nPin, PinName in enumerate(East):
            Offset = self.LocToSWOffset + self.Height + np.array([self.Width, -nPin-1])
            self.Pins[f"E.{nPin}"] = ComponentPin(self, Offset, 'E')
            self.text(*(self.Location + self.LocToSWOffset + self.Height + np.array([self.Width-1, -nPin-1])), s=PinName, color = Colors.Components.build, va = 'center', ha = 'right')

    def Fix(self, var):
        ComponentBase.Fix(var)
        for Pin in self.Pins.values():
            Pin.Fix(var)

    @property
    def CasingSides(self):
        Offset = RotateOffset(self.LocToSWOffset, self.Rotation)
        x,y = self.Location + RotateOffset(self.LocToSWOffset, self.Rotation)
        X,Y = self.Location + RotateOffset(self.LocToSWOffset + np.array([self.Width, self.Height]), self.Rotation)
        return (((x,x), (y,Y)), # West
                ((x,X), (Y,Y)), # North
                ((X,X), (Y,y)), # East
                ((X,x), (y,y))) # South

def RotateOffset(Offset, Rotation): # Use LRU ?
    RotValue = (Rotation & 0b11)
    if RotValue == 0:
        return Offset
    if RotValue == 1:
        return np.array([-Offset[1], Offset[0]])
    if RotValue == 2:
        return -Offset
    if RotValue == 3:
        return np.array([Offset[1], -Offset[0]])

class Wire(ComponentBase):
    BuildMode = Params.GUI.Behaviour.DefaultBuildMode
    DefaultLinewidth = Params.GUI.PlotsWidths.Wire
    DefaultMarkersize = 0
    CName = "Wire"
    def __init__(self, StartLocation, EndLocation = None):
        ComponentBase.__init__(self, StartLocation)

        self.Points = np.zeros((3,2), dtype = int)
        self.plot(self.Points[:2,0], self.Points[:2,1], color = Colors.Components.build, linestyle = Params.GUI.PlotsStyles.Wire, linewidth = self.DefaultLinewidth)
        self.plot(self.Points[1:,0], self.Points[1:,1], color = Colors.Components.build, linestyle = Params.GUI.PlotsStyles.Wire, linewidth = self.DefaultLinewidth)
        self.Points[0,:] = StartLocation
        if EndLocation is None:
            self.Points[2,:] = StartLocation
        else:
            self.Points[2,:] = EndLocation
        self.UpdateLocation()

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

    def UpdateLocation(self):
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
        self.UpdateLocation()

class Connexion(ComponentBase):
    CName = "Connexion"
    DefaultLinewidth = 0
    DefaultMarkersize = Params.GUI.PlotsWidths.Connexion
    def __init__(self, Location, Column): # Warning : 0 is stored in sets, to avoid many checks.
        ComponentBase.__init__(self, Location)
        self.Fixed = True

        self.IDs = set(Column[:8]) # Set to avoid unnecessary storage
        self.NWires = (Column[:8] > 0).sum()
        
        self.plot(self.Location[0], self.Location[1], marker = Params.GUI.PlotsStyles.Connexion, markersize = self.DefaultMarkersize, color = Colors.Components.fixed)
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

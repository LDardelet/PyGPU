import numpy as np
import matplotlib.pyplot as plt

import types
from importlib import reload
from Values import Colors, Params, PinDict, Levels
from Console import Log, LogSuccess, LogWarning, LogError
from Storage import StorageItem

class StateHandler(StorageItem):
    LibRef = 'StateHandler'
    class States:
        Building = 0
        Fixed = 1
        Removing = 2
        Selected = 3
    def __init__(self, Comp, StartState = 0): # Starts building by default
        self.StoreAttribute('Comp', Comp)
        self.StoreAttribute('State', StartState)
    @property
    def Building(self):
        return self.State == self.States.Building
    @property
    def Fixed(self):
        return self.State == self.States.Fixed
    def Fix(self):
        self.State = self.States.Fixed
        self.UpdateColor()
    @property
    def Selected(self):
        return self.State == self.States.Selected
    def Select(self):
        self.State = self.States.Selected
        self.UpdateColor()
    def UpdateColor(self):
        Color = self.Color
        for Plot in self.Comp.LevelsPlots:
            Plot.set_color(Color)
        Color = self.NeutralColor
        for Plot in self.Comp.NeutralPlots:
            Plot.set_color(Color)
    @property
    def Color(self):
        if not self.Fixed or self.Comp.Group is None:
            return Colors.Component.Modes[self.State]
        else:
            return self.Comp.Group.Color
    @property
    def NeutralColor(self):
        return Colors.Component.Modes[self.State]

class ComponentBase(StorageItem):
    Board = None
    DefaultLinewidth = 0
    DefaultMarkersize = 0
    RotationAllowed = True
    CName = None
    Book = None
    def __init__(self, Location=None, Rotation=None): # As base for components, only one we cannot remove default arguments
        self.StoreAttribute('Location', Location)
        self.StoreAttribute('Rotation', Rotation)
        self.StoreAttribute('ID', None)
        self.StoreAttribute('State', StateHandler(self))
        self.StoreAttribute('Group', None)
        self.StoreAttribute('Children', set())
        self.StoreAttribute('Links', set())

    def Start(self):
        self.Highlighted = False
        self.Plots = []
        self.HighlightPlots = []
        self.LevelsPlots = []
        self.NeutralPlots = []

        self.PlotInit()

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

    def Fix(self):
        if self.State.Fixed:
            raise ValueError("Component already fixed")
        self.State.Fix()

    def LinkedTo(self, ID):
        return ID in self.Links

    def Select(self, var):
        if var:
            if self.State.Selected:
                self.State.Fix() # If we select again a selected component, it means we unselect it
            self.State.Select()
        else:
            if not self.State.Selected:
                raise ValueError("Component not selected")
            self.State.Fix()

    @property
    def CanFix(self): # Property that ensures all condition have been checked for this component to be fixed
        return True

    def Drag(self, Cursor):
        pass

    def PlotInit(self):
        pass

    def plot(self, *args, Highlight = True, LevelPlot = True, **kwargs):
        Plot = self.Board.plot(*args, **kwargs)[0]
        self.Plots.append(Plot)
        if LevelPlot:
            self.LevelsPlots.append(Plot)
        else:
            self.NeutralPlots.append(Plot)
        if Highlight:
            self.HighlightPlots.append(Plot)
    def text(self, *args, LevelPlot = False, **kwargs): # Cannot highlight text, would get messy
        Text = self.Board.text(*args, **kwargs)
        self.Plots.append(Text)
        if LevelPlot:
            self.LevelsPlots.append(Text)
        else:
            self.NeutralPlots.append(Text)

    def Rotate(self):
        if not self.RotationAllowed:
            return
        self.Rotation += 1
        self.UpdateLocation()

    @property
    def InputReady(self): # Base components are not ready as they should not be updated (wires, connexions, ...)
        return False
    def UpdateLevel(self):
        self.State.UpdateColor()
    def __call__(self):
        pass

    @property
    def Location(self):
        return self._Location
    @Location.setter
    def Location(self, Location):
        if not Location is None:
            self._Location = np.array(Location)
        else:
            self._Location = np.zeros(2, dtype = int)
    @property
    def Rotation(self):
        return self._Rotation
    @Rotation.setter
    def Rotation(self, Rotation):
        if not Rotation is None:
            self._Rotation = Rotation
        else:
            self._Rotation = 0
    @property
    def AdvertisedLocations(self):
        return np.zeros((0,3), dtype = int)
    @property
    def AdvertisedConnexions(self):
        return np.zeros((0,2), dtype = int)
    @property
    def Size(self):
        return self.AdvertisedLocations.shape[0]
    @property
    def Extent(self):
        return (self.AdvertisedLocations[:,0].min(), self.AdvertisedLocations[:,1].min(), self.AdvertisedLocations[:,0].max(), self.AdvertisedLocations[:,1].max())

    def Clear(self): # Falls back from temporary state to fixed state, or removed
        if self.State.Building:
            self.destroy()
        elif self.State.Selected:
            self.Select(False)

    def destroy(self):
        for plot in self.Plots:
            plot.remove()

    def __repr__(self):
        return f"{self.CName} ({self.ID})"
    @property
    def LibRef(self):
        return f"{self.Book}.{self.CName}"

class CasedComponent(ComponentBase): # Template to create any type of component
    DefaultLinewidth = Params.GUI.PlotsWidths.Casing
    InputPinsDef = None
    OutputPinsDef = None
    Callback = None
    Schematics = None
    ForceWidth = None
    ForceHeight = None
    DisplayPinNumbering = None
    Symbol = ''
    def __init__(self, Location, Rotation):
        super().__init__(Location, Rotation)
        self.StoreAttribute('InputPins', [])
        self.StoreAttribute('OutputPins', [])

        self.Start()

        def PinKey(Side, Index):
            return f"{Side}.{Offset}"
        for nPin, ((Side, Index), Name) in enumerate(self.InputPinsDef + self.OutputPinsDef):
            if nPin < len(self.InputPinsDef):
                PinsList = self.InputPins
                Type = PinDict.Input
            else:
                PinsList = self.OutputPins
                Type = PinDict.Output
            if self.DisplayPinNumbering:
                if not Name:
                    Name = str(nPin)
                else:
                    Name = f"{nPin} ({Name})"
            if Side == PinDict.W:
                Offset = self.LocToSWOffset + np.array([0, self.Height-Index-1])
            elif Side == PinDict.E:
                Offset = self.LocToSWOffset + np.array([self.Width, self.Height-Index-1])
            elif Side == PinDict.N:
                Offset = self.LocToSWOffset + np.array([1+Index, self.Height])
            elif Side == PinDict.S:
                Offset = self.LocToSWOffset + np.array([1+nPin, 0])
            else:
                raise ValueError(f"Wrong component {self.__class__.__name__} definition")
            Pin = ComponentPin(self, Offset, Side, Type, Index, Name)
            self.Children.add(Pin)
            PinsList.append(Pin)

    def Start(self):
        self.Width = 1
        self.Height = 1
        for (Side, Index), Name in self.InputPinsDef+self.OutputPinsDef:
            if Side == PinDict.W or Side == PinDict.E:
                self.Width = max(self.Width, Index+1)
            else:
                self.Height= max(self.Height,Index+1)

        if self.ForceWidth:
            if self.Width > self.ForceWidth:
                raise ValueError(f"Unable to place all pins on component {self.CName} with constrained width {self.ForceWidth}")
            self.Width = self.ForceWidth
        else:
            self.Width = max(self.Width, Params.Board.ComponentMinWidth)
        if self.ForceHeight:
            if self.Height > self.ForceHeight:
                raise ValueError(f"Unable to place all pins on component {self.CName} with constrained height {self.ForceHeight}")
            self.Height = self.ForceHeight
        else:
            self.Height = max(self.Height, Params.Board.ComponentMinHeight)

        self.LocToSWOffset = -np.array([self.Width//2, self.Height//2])

        if self.Callback is None:
            if self.Schematics is None:
                raise ValueError("Component must have exactly a callback or an inner schematics to run (0 given)")
            self.Run = self.Schematics.Run
        else:
            if not self.Schematics is None:
                raise ValueError("Component must have exactly a callback or an inner schematics to run (2 given)")
            self.Run = self.__class__.Callback

        super().Start()

    def __call__(self):
        if not self.InputReady:
            return
        for Pin, Level in zip(self.OutputPins, self.Run(*self.Input)):
            Pin.Group.SetLevel(Level, Pin)

    @property
    def Input(self):
        return [Pin.Group.Level for Pin in self.InputPins]
    @property
    def Output(self):
        return [Pin.Group.Level for Pin in self.OutputPins]
    @property
    def InputReady(self):
        return (not None in self.Input)

    def Drag(self, Cursor):
        self.Location = np.array(Cursor)
        self.UpdateLocation()

    def Contains(self, Location):
        P1 = self.Location + RotateOffset(self.LocToSWOffset, self.Rotation)
        P2 = self.Location + RotateOffset(self.LocToSWOffset + np.array([self.Width, self.Height]), self.Rotation)
        return (Location >= np.minimum(P1, P2)).all() and (Location <= np.maximum(P1, P2)).all()

    def UpdateLocation(self):
        for Plot, (Xs, Ys) in zip(self.Plots[:4], self.CasingSides):
            Plot.set_data(Xs, Ys)
        TLoc = self.TextLocation
        self.Plots[4].set_x(TLoc[0])
        self.Plots[4].set_y(TLoc[1])
        self.Plots[4].set_rotation(self.TextRotation)

        for Pin in self.Children:
            Pin.UpdateLocation()

    def PlotInit(self):
        for Xs, Ys in self.CasingSides:
            self.plot(Xs, Ys, color = self.State.Color, linestyle = Params.GUI.PlotsStyles.Casing, linewidth = self.DefaultLinewidth, LevelPlot = False)

        self.text(*self.TextLocation, s = (self.CName, self.Symbol)[bool(self.Symbol)], color = self.State.Color, va = 'center', ha = 'center', rotation = self.TextRotation)

    @property
    def TextLocation(self):
        return self.Location + RotateOffset(self.LocToSWOffset + np.array([self.Width, self.Height])/2, self.Rotation)
    @property
    def TextRotation(self):
        if self.Symbol:
            return 0 # If it is a symbol, must be plotted correctly at all times
        return ((self.Rotation + (self.Width <= 10))%4)*90

    @property
    def CasingSides(self):
        Offset = RotateOffset(self.LocToSWOffset, self.Rotation)
        x,y = self.Location + RotateOffset(self.LocToSWOffset, self.Rotation)
        X,Y = self.Location + RotateOffset(self.LocToSWOffset + np.array([self.Width, self.Height]), self.Rotation)
        return (((x,x), (y,Y)), # West
                ((x,X), (Y,Y)), # North
                ((X,X), (Y,y)), # East
                ((X,x), (y,y))) # South

    def destroy(self):
        super().destroy()
        for Pin in self.Children:
            Pin.destroy()

    def Highlight(self, var):
        super().Highlight(var)
        for Pin in self.Children:
            Pin.Highlight(var)
    def Select(self, var):
        super().Select(var)
        for Pin in self.Children:
            Pin.Select(var)

    @property
    def AdvertisedLocations(self):
        if Params.Board.CasingsOwnPinsBases: # Use if pins bases are considered casing parts
            Locations = np.zeros((9*len(self.Children),3), dtype = int)
            for nPin, Pin in enumerate(self.Children):
                Locations[9*nPin:9*(nPin+1),:2] = Pin.PinBaseLocation
                Locations[9*nPin:9*(nPin+1),-1] = np.arange(9)
            return Locations
        else:
            return np.zeros((0,3), dtype = int)

class ComponentPin(ComponentBase):
    DefaultLinewidth = Params.GUI.PlotsWidths.Wire
    DefaultMarkersize = 0
    CName = "Pin"
    LibRef = "Pin"
    def __init__(self, Parent, PinBaseOffset, Side, Type, Index, Name = ''):
        super().__init__()
        self.StoreAttribute('Parent', Parent)
        self.StoreAttribute('PinBaseOffset', PinBaseOffset)
        self.StoreAttribute('Side', Side)
        self.StoreAttribute('Type', Type)
        self.StoreAttribute('Index', Index)
        self.StoreAttribute('Name', Name)

        self.Start()

    def Start(self):
        self.BaseRotation = {PinDict.E:0,
                             PinDict.N:1,
                             PinDict.W:2,
                             PinDict.S:3}[self.Side]
        self.Vector = Params.Board.ComponentPinLength * RotateOffset(np.array([1, 0]), self.BaseRotation)
        self.Offset = self.PinBaseOffset + self.Vector

        super().Start()

    def PlotInit(self):
        Loc = self.Location
        BLoc = self.PinBaseLocation
        self.plot([Loc[0], BLoc[0]], [Loc[1], BLoc[1]], color = self.State.Color, linestyle = Params.GUI.PlotsStyles.Wire, linewidth = self.DefaultLinewidth)
        if self.Name:
            self.text(*self.TextLocation, s=self.Name, LevelPlot = Params.GUI.PlotsStyles.PinNameLevelColored, color = self.State.Color, **PinNameDict(self.Rotation + self.BaseRotation))

    def UpdateLocation(self):
        Loc = self.Location
        BLoc = self.PinBaseLocation
        self.Plots[0].set_data([Loc[0], BLoc[0]], [Loc[1], BLoc[1]])
        if self.Name:
            TLoc = self.TextLocation
            self.Plots[1].set_x(TLoc[0])
            self.Plots[1].set_y(TLoc[1])
            self.Plots[1].set(**PinNameDict(self.Rotation + self.BaseRotation))

    @property
    def Location(self):
        return self.Parent.Location + RotateOffset(self.Offset, self.Rotation)
    @Location.setter
    def Location(self, Location):
        pass
    @property
    def Rotation(self):
        return self.Parent.Rotation
    @Rotation.setter
    def Rotation(self, Rotation):
        pass
    @property
    def PinBaseLocation(self):
        return self.Parent.Location + RotateOffset(self.PinBaseOffset, self.Rotation)
    @property
    def TextLocation(self):
        return self.Parent.Location + RotateOffset(self.PinBaseOffset - self.Vector, self.Rotation)

    def UpdateLevel(self):
        super().UpdateLevel()
        if self.Type == PinDict.Input:
            self.Parent()
    @property
    def AdvertisedLocations(self):
        if Params.Board.CasingsOwnPinsBases:
            return np.array([[self.Location[0], self.Location[1], ((self.Rotation+self.BaseRotation+2)%4)*2]])
        else:
            Locations = np.zeros((10,3), dtype = int)
            Locations[:9,:2] = self.PinBaseLocation
            Locations[:9,-1] = np.arange(9)
            Locations[-1,:]  = self.Location[0], self.Location[1], ((self.Rotation+self.BaseRotation+2)%4)*2
            return Locations
    @property
    def AdvertisedConnexions(self):
        return self.Location.reshape((1,2))

    def __repr__(self):
        return f"{self.Parent} {PinDict.PinTypeNames[self.Type]} {self.Name}"

def PinNameDict(Rotation):
    SideIndex = Rotation & 0b11
    return {'rotation':('horizontal', 'vertical', 'horizontal', 'vertical')[SideIndex],
            'va':('center', 'bottom', 'center', 'top')[SideIndex],
            'ha':('left', 'center', 'right', 'center')[SideIndex]}

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
    DefaultLinewidth = Params.GUI.PlotsWidths.Wire
    DefaultMarkersize = 0
    CName = "Wire"
    def __init__(self, Location, Rotation):
        super().__init__(Location, Rotation)
        self.StoreAttribute('BuildMode', self.__class__.BuildMode)

        self.Start()

    def SetBuildMode(self, mode):
        self.BuildMode = mode
        self.UpdateLocation()

    def PlotInit(self):
        self.plot(self.Location[:2,0], self.Location[:2,1], color = self.State.Color, linestyle = Params.GUI.PlotsStyles.Wire, linewidth = self.DefaultLinewidth)
        self.plot(self.Location[1:,0], self.Location[1:,1], color = self.State.Color, linestyle = Params.GUI.PlotsStyles.Wire, linewidth = self.DefaultLinewidth)
        self.UpdateLocation()

    @property
    def Location(self):
        return self._Location
    @Location.setter
    def Location(self, Location):
        self._Location = np.zeros((3,2), dtype = int)
        if not Location is None:
            self._Location[(0,2),:] = np.array(Location)
    @property
    def AdvertisedLocations(self):
        AdvertisedLocations = []
        P1, P2, P3 = self.Location
        (A1, A2), (D1, D2) = self.Angles
        if (P2 != P1).any():
            AdvertisedLocations.append((P1[0], P1[1], A1+D1))
            for x, y in np.linspace(P1, P2, abs(P2-P1).max()+1, dtype = int)[1:-1]:
                AdvertisedLocations.append((x,y,A1))
                AdvertisedLocations.append((x,y,A1+4))
            AdvertisedLocations.append((P2[0], P2[1], (A1+D1+4)%8))
        if (P3 != P2).any():
            AdvertisedLocations.append((P2[0], P2[1], A2+D2))
            for x, y in np.linspace(P2, P3, abs(P3-P2).max()+1, dtype = int)[1:-1]:
                AdvertisedLocations.append((x,y,A2))
                AdvertisedLocations.append((x,y,A2+4))
            AdvertisedLocations.append((P3[0], P3[1], (A2+D2+4)%8))
        return np.array(AdvertisedLocations)
    @property
    def AdvertisedConnexions(self):
        return self.Location[(0,2),:2]

    def UpdateLocation(self):
        if self.BuildMode == 0: # Straight wires
            if (self.Rotation & 0b1) == 0:
                self.Location[1,0] = self.Location[2,0]
                self.Location[1,1] = self.Location[0,1]
            else:
                self.Location[1,0] = self.Location[0,0]
                self.Location[1,1] = self.Location[2,1]
        else:
            Offsets = self.Location[2,:] - self.Location[0,:]
            Lengths = abs(Offsets)
            StraightAxis = Lengths.argmax()
            SignStraight = np.sign(Offsets[StraightAxis])
            Offsets[1-StraightAxis] = 0
            Offsets[StraightAxis] -= SignStraight * Lengths.min()
            if (self.Rotation & 0b1) == 0:
                self.Location[1,:] = self.Location[0,:] + Offsets
            else:
                self.Location[1,:] = self.Location[2,:] - Offsets
        self.Plots[0].set_data(self.Location[:2,0], self.Location[:2,1])
        self.Plots[1].set_data(self.Location[1:,0], self.Location[1:,1])

    @property
    def Angles(self):
        Offsets = self.Location[1:,:] - self.Location[:2,:]
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
        self.Location[2,:] = Cursor
        self.UpdateLocation()

    @property
    def CanFix(self):
        return (self.Location[0,:] != self.Location[2,:]).any()

    def __repr__(self):
        return f"{self.CName} ({self.ID})"

class Connexion(ComponentBase):
    CName = "Connexion"
    LibRef = "Connexion"
    DefaultLinewidth = 0
    DefaultMarkersize = Params.GUI.PlotsWidths.Connexion
    def __init__(self, Location, Column): # Warning : 0 is stored in sets, to avoid many checks.
        super().__init__(Location)
        IDs, NWires = self.GetConnexionInfo(Column)
        self.StoreAttribute('IDs', IDs)
        self.StoreAttribute('NWires', NWires)

        self.Start()
        self.State.Fix()

    def PlotInit(self):
        self.plot(self.Location[0], self.Location[1], Highlight = False, marker = Params.GUI.PlotsStyles.Connexion, markersize = self.DefaultMarkersize, color = self.State.Color)
        self.CheckDisplay()

    def UpdateConnexions(self, Column):
        self.IDs, self.NWires = self.GetConnexionInfo(Column)
        self.CheckDisplay()

    @staticmethod
    def GetConnexionInfo(Column):
        return set(Column[:8]), (Column[:8] > 0).sum()

    def CheckDisplay(self):
        if self.NWires >= 3:
            self.Plots[0].set_alpha(1.)
        else:
            self.Plots[0].set_alpha(0.)

    @property
    def Displayed(self):
        return self.NWires >= 3

    @property
    def AdvertisedLocations(self):
        return np.array([[self.Location[0], self.Location[1], -1]])

import numpy as np
import matplotlib.pyplot as plt

from functools import cached_property

from Values import Colors, Params, PinDict, Levels
from Console import Log, LogSuccess, LogWarning, LogError
from Storage import StorageItem

class StatesC(StorageItem):
    Names = ['Building',
             'Fixed',
             'Removing', 
             'Selected']
    LibRef = "StatesC"
    def __init__(self):
        self.StoredAttribute('States', set())
        for Value, State in enumerate(self.Names):
            StateClassName = State+'C'
            NewStateC = type(StateClassName,
                               (StateC, ),
                               {
                                   'LibRef' : StateClassName,
                                   'Name'   : State,
                                   'Value'  : Value,
                                })
            NewState = NewStateC(self)
            setattr(self, State, NewState)
            self.States.add(NewState)

class StateC(StorageItem):
    Value = None
    Name = None
    LibRef = None
    def __init__(self, States):
        self.StoredAttribute('Parent', States) # Ensures that the 4 states are all saved, and all created when loading
        for Value, State in enumerate(self.Parent.Names):
            self.StoredAttribute(State, Value == self.Value)
    def __repr__(self):
        return self.Name + "_repr"
    @cached_property
    def Color(self):
        return Colors.Component.Modes[self.Value]
    @cached_property
    def Alpha(self):
        if self.Selected:
            return Params.GUI.PlotsStyles.AlphaSelection
        return 1.

States = StatesC()

def Parenting(func):
    def ParentedFunction(self, *args, **kwargs):
        for Child in self.Children:
            getattr(Child, func.__name__)(*args, **kwargs)
        return func(self, *args, **kwargs)
    return ParentedFunction

class ComponentBase(StorageItem):
    Display = None
    DefaultLinewidth = 0
    DefaultMarkersize = 0
    RotationAllowed = True
    CName = None
    Book = None
    def __init__(self, Location=None, Rotation=None): # As base for components, only one we cannot remove default arguments
        self.StoredAttribute('Location', Location)
        self.StoredAttribute('Rotation', Rotation)
        self.StoredAttribute('ID', None)
        self.StoredAttribute('State', States.Building)
        self.StoredAttribute('Group', None)
        self.StoredAttribute('Children', set())
        self.StoredAttribute('Links', set())

    def __getattr__(self, State): # Overriding getattr to handle state checking
        if State in StatesC.Names:
            return getattr(self.State, State)
        raise AttributeError(f"{State} is not an attribute of {self.__class__} nor a valid state")

    def Start(self):
        self.Highlighted = False
        self.Plots = []
        self.HighlightPlots = []
        self.LevelsPlots = []
        self.NeutralPlots = []

        self.PlotInit()

    @Parenting
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
        return
    @Parenting
    def Fix(self):
        if self.State.Fixed:
            return set()
        self.State = States.Fixed
        self.UpdateStyle()
        return {self}
    @Parenting
    def Select(self):
        if self.State.Selected:
            return set()
        self.State = States.Selected
        self.UpdateStyle()
        return {self}
    @Parenting
    def StartRemoving(self):
        if self.State.Removing:
            return set()
        self.State = States.Removing
        self.UpdateStyle()
        return {self}
    @Parenting
    def destroy(self):
        for plot in self.Plots:
            plot.remove()

    def LinkedTo(self, Component):
        return Component in self.Links

    @property
    def CanFix(self): # Property that ensures all condition have been checked for this particular component to be fixed
        return True
    def Drag(self, Cursor):
        pass
    def PlotInit(self):
        pass

    @property
    def Color(self):
        if self.State.Fixed or self.State.Selected:
            return self.Group.Color
        else:
            return self.State.Color
    @property
    def NeutralColor(self):
        return self.State.Color
    @property
    def Alpha(self):
        return self.State.Alpha

    def UpdateStyle(self):
        Color, NeutralColor, Alpha = self.Color, self.NeutralColor, self.Alpha
        for Plot in self.LevelsPlots:
            Plot.set_color(Color)
            Plot.set_alpha(Alpha)
        for Plot in self.NeutralPlots:
            Plot.set_color(NeutralColor)
            Plot.set_alpha(Alpha)

    def plot(self, *args, Highlight = True, LevelPlot = True, **kwargs):
        Plot = self.Display.plot(*args, **kwargs)[0]
        self.Plots.append(Plot)
        if LevelPlot:
            self.LevelsPlots.append(Plot)
        else:
            self.NeutralPlots.append(Plot)
        if Highlight:
            self.HighlightPlots.append(Plot)
    def circle(self, *args, LevelPlot = True, **kwargs):
        C = plt.Circle(*args, **kwargs)
        self.Plots.append(C)
        self.Display.add_patch(C)
        if LevelPlot:
            self.LevelsPlots.append(C)
        else:
            self.NeutralPlots.append(C)
    def text(self, *args, LevelPlot = False, **kwargs): # Cannot highlight text, would get messy
        Text = self.Display.text(*args, **kwargs)
        self.Plots.append(Text)
        if LevelPlot:
            self.LevelsPlots.append(Text)
        else:
            self.NeutralPlots.append(Text)

    @Parenting # Potential issue here
    def Rotate(self):
        if not self.RotationAllowed:
            return
        self.Rotation += 1
        self.UpdateLocation()

    @property
    def InputReady(self): # Base components are not ready by default as they should not be updated (wires, connexions, ...)
        return False
    def __call__(self):
        return False
    @property
    def Level(self):
        if self.Group is None:
            return Levels.Undef
        return self.Group.Level
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
    @property
    def TriggersParent(self):
        return False

    def Clear(self): # Falls back from temporary state to fixed state, or removed
        if self.State.Building:
            self.destroy()
        elif self.State.Selected or self.State.Removing:
            self.Fix()

    def __repr__(self):
        return f"{self.CName} ({self.ID})"
    @property
    def LibRef(self):
        return f"{self.Book}.{self.CName}"

class BoardPinC(ComponentBase):
    DefaultLinewidth = Params.GUI.PlotsWidths.Pin
    DefaultMarkersize = 0
    CName = "Board Pin"
    LibRef = "BoardPin"
    def __init__(self, Location, Rotation):
        super().__init__(Location, Rotation)
        self.StoredAttribute('_Type', PinDict.Output)      # Input or output. Output by default, avoids to SetLevel group (board inputs are components inputs, thus are set externally)
        self.StoredAttribute('DefinedLevel', Levels.Undef)
        self.StoredAttribute('_PinLabelRule', 0b11)
        self.StoredAttribute('Side', None)
        self.StoredAttribute('_Index', None)
        self.StoredAttribute('_Name', '')

        self.Start()

    def PlotInit(self):
        Loc = self.Location
        BLoc = self.PinBaseLocation
        Color, Alpha = self.Color, self.Alpha
        self.plot([Loc[0], BLoc[0]], [Loc[1], BLoc[1]], color = Color, linestyle = Params.GUI.PlotsStyles.Pin, linewidth = self.DefaultLinewidth, alpha = Alpha)
        self.text(*self.TextLocation, s=self.Label, LevelPlot = Params.GUI.PlotsStyles.PinNameLevelColored, color = Color, alpha = Alpha, **PinNameDict(self.Rotation))
        self.circle(BLoc, radius = 0.5, color = Color, fill = False, linewidth = self.DefaultLinewidth, alpha = Alpha)

    def Drag(self, Cursor):
        self.Location = np.array(Cursor)
        self.UpdateLocation()

    @property
    def Level(self):
        return self.Group.Level
    @Level.setter
    def Level(self, Level):
        if self.Type == PinDict.Input:
            self.Group.SetLevel(Level, self)
        else:
            raise Exception("Attempting to set level of a board output")
    @property
    def PinLabelRule(self):
        return self._PinLabelRule
    @PinLabelRule.setter
    def PinLabelRule(self, value):
        self._PinLabelRule = value
        self.Plots[1].set_text(self.Label)
    @property
    def Index(self):
        return self._Index
    @Index.setter
    def Index(self, Index):
        self._Index = Index
        self.Plots[1].set_text(self.Label)
    @property
    def Name(self):
        return self._Name
    @Name.setter
    def Name(self, Name):
        self._Name = Name
        self.Plots[1].set_text(self.Label)

    @property
    def Type(self):
        return self._Type
    @Type.setter
    def Type(self, Value):
        if self._Type == Value:
            return
        self._Type = Value
        if Value == PinDict.Input:
            self.Group.SetLevel(self.DefinedLevel, self)
        elif Value == PinDict.Output:
            self.Group.RemoveLevelSet(self)
        else:
            raise Exception(f"Wrong {self} type {Value}")
        Log(f"{self.Label} {self.CName} type set to {PinDict.PinTypeNames[self.Type]}")

    @property
    def Label(self):
        return PinLabel(self.PinLabelRule, self.Index, self.Name)
    @property
    def PinBaseLocation(self):
        return self.Location + RotateOffset(np.array([-1, 0]), self.Rotation)
    @property
    def TextLocation(self):
        return self.Location + RotateOffset(np.array([-2, 0]), self.Rotation)

    def UpdateLocation(self):
        Loc = self.Location
        BLoc = self.PinBaseLocation
        self.Plots[0].set_data([Loc[0], BLoc[0]], [Loc[1], BLoc[1]])
        self.Plots[1].set_position(self.TextLocation)
        self.Plots[1].set(**PinNameDict(self.Rotation))
        self.Plots[2].set_center(BLoc)

    @property
    def AdvertisedLocations(self):
        Locations = np.zeros((10,3), dtype = int)
        Locations[:9,:2] = self.PinBaseLocation
        Locations[:9,-1] = np.arange(9)
        Locations[-1,:]  = self.Location[0], self.Location[1], ((self.Rotation+2)%4)*2
        return Locations
    @property
    def AdvertisedConnexions(self):
        return self.Location.reshape((1,2))

    def __repr__(self):
        return f"{PinDict.PinTypeNames[self.Type]} {self.CName} " + self.Label

class CasedComponentC(ComponentBase): # Template to create any type of component
    DefaultLinewidth = Params.GUI.PlotsWidths.Casing
    InputPinsDef = None
    OutputPinsDef = None
    Callback = None
    Board = None
    ForceWidth = None
    ForceHeight = None
    PinLabelRule = None
    Symbol = ''
    def __init__(self, Location, Rotation):
        super().__init__(Location, Rotation)
        self.StoredAttribute('InputPins', [])
        self.StoredAttribute('OutputPins', [])

        self.Start()

        for nPin, ((Side, Index), Name) in enumerate(self.InputPinsDef + self.OutputPinsDef):
            if nPin < len(self.InputPinsDef):
                PinsList = self.InputPins
                PinClass = InputPinC
            else:
                PinsList = self.OutputPins
                PinClass = OutputPinC
            Pin = PinClass(self, Side, Index, Name)
            self.Children.add(Pin)
            PinsList.append(Pin)

    def Start(self):
        if self.Callback is None:
            if self.Board is None:
                raise ValueError("Component must have exactly a callback or an inner schematics to run (0 given)")
            self.Run = self.Board.Run
        else:
            if not self.Board is None:
                raise ValueError("Component must have exactly a callback or an inner schematics to run (2 given)")
            self.Run = self.__class__.Callback

        super().Start()

    @cached_property
    def Width(self):
        Width = 1
        for (Side, Index), Name in self.InputPinsDef+self.OutputPinsDef:
            if Side == PinDict.W or Side == PinDict.E:
                Width = max(Width, Index+1)
        if self.ForceWidth:
            if Width > self.ForceWidth:
                raise ValueError(f"Unable to place all pins on component {self.CName} with constrained width {self.ForceWidth}")
            return self.ForceWidth
        else:
            return max(Width, Params.Board.ComponentMinWidth)

    @cached_property
    def Height(self):
        Height = 1
        for (Side, Index), Name in self.InputPinsDef+self.OutputPinsDef:
            if Side == PinDict.N or Side == PinDict.S:
                Height= max(Height,Index+1)
        if self.ForceHeight:
            if Height > self.ForceHeight:
                raise ValueError(f"Unable to place all pins on component {self.CName} with constrained height {self.ForceHeight}")
            return self.ForceHeight
        else:
            return max(Height, Params.Board.ComponentMinHeight)

    @cached_property
    def LocToSWOffset(self):
        return -np.array([self.Width//2, self.Height//2])

    def __call__(self):
        if not self.InputReady:
            return False
        Level = self.Level
        for Pin, Level in zip(self.OutputPins, self.Run(*self.Input)):
            Pin.Level = Level
        return self.Level != Level
    @property
    def Input(self):
        return [Pin.Level for Pin in self.InputPins]
    @property
    def Output(self):
        return [Pin.Level for Pin in self.OutputPins]
    @property
    def Level(self): # We define a cased component level as the binary representation of its output
        if not self.InputReady:
            return 0
        Level = 0
        for nPin, Pin in enumerate(self.OutputPins):
            Level |= Pin.Level << nPin
        return Level

    @property
    def Color(self):
        return self.NeutralColor

    @property
    def InputReady(self):
        for Level in self.Input:
            if Level >> 1:
                return False
        return True

    def Drag(self, Cursor):
        self.Location = np.array(Cursor)
        self.UpdateLocation()

    def __contains__(self, Location):
        P1 = self.Location + RotateOffset(self.LocToSWOffset, self.Rotation)
        P2 = self.Location + RotateOffset(self.LocToSWOffset + np.array([self.Width, self.Height]), self.Rotation)
        return (Location >= np.minimum(P1, P2)).all() and (Location <= np.maximum(P1, P2)).all()

    @Parenting
    def UpdateLocation(self):
        for Plot, (Xs, Ys) in zip(self.Plots[:4], self.CasingSides):
            Plot.set_data(Xs, Ys)
        TLoc = self.TextLocation
        self.Plots[4].set_x(TLoc[0])
        self.Plots[4].set_y(TLoc[1])
        self.Plots[4].set_rotation(self.TextRotation)

    def PlotInit(self):
        Color, Alpha = self.Color, self.Alpha
        for Xs, Ys in self.CasingSides:
            self.plot(Xs, Ys, color = Color, linestyle = Params.GUI.PlotsStyles.Casing, linewidth = self.DefaultLinewidth, alpha = Alpha, LevelPlot = False)
        self.text(*self.TextLocation, s = (self.CName, self.Symbol)[bool(self.Symbol)], color = Color, va = 'center', ha = 'center', rotation = self.TextRotation, alpha = Alpha)

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

class ComponentPinC(ComponentBase):
    DefaultLinewidth = Params.GUI.PlotsWidths.Pin
    DefaultMarkersize = 0
    CName = "Pin"
    LibRef = "Pin"
    def __init__(self, Parent, Side, Index, Name = ''):
        super().__init__()
        self.StoredAttribute('Parent', Parent)
        self.StoredAttribute('Side', Side)
        self.StoredAttribute('Index', Index)
        self.StoredAttribute('Name', Name)

        self.Start()

    @cached_property
    def PinBaseOffset(self):
        if self.Side == PinDict.W:
            return self.Parent.LocToSWOffset + np.array([0, self.Parent.Height-self.Index-1])
        elif self.Side == PinDict.E:
            return self.Parent.LocToSWOffset + np.array([self.Parent.Width, self.Parent.Height-self.Index-1])
        elif self.Side == PinDict.N:
            return self.Parent.LocToSWOffset + np.array([1+self.Index, self.Parent.Height])
        elif self.Side == PinDict.S:
            return self.Parent.LocToSWOffset + np.array([1+self.Index, 0])
        else:
            raise ValueError(f"Wrong component {self.Parent.CName} definition for pin {self.Index}")
    @cached_property
    def BaseRotation(self):
        return {PinDict.E:0,
                PinDict.N:1,
                PinDict.W:2,
                PinDict.S:3}[self.Side]

    @cached_property
    def Offset(self):
        return self.PinBaseOffset + Params.Board.ComponentPinLength * RotateOffset(np.array([1, 0]), self.BaseRotation)
    @cached_property
    def TextBaseOffset(self):
        return self.PinBaseOffset - Params.Board.ComponentPinLength * RotateOffset(np.array([1, 0]), self.BaseRotation)

    def PlotInit(self):
        Loc = self.Location
        BLoc = self.PinBaseLocation
        Color, Alpha = self.Color, self.Alpha
        self.plot([Loc[0], BLoc[0]], [Loc[1], BLoc[1]], color = Color, linestyle = Params.GUI.PlotsStyles.Pin, linewidth = self.DefaultLinewidth, alpha = Alpha)
        self.text(*self.TextLocation, s=self.Label, LevelPlot = Params.GUI.PlotsStyles.PinNameLevelColored, color = Color, alpha = Alpha, **PinNameDict(self.Rotation + self.BaseRotation))

    def UpdateLocation(self):
        Loc = self.Location
        BLoc = self.PinBaseLocation
        self.Plots[0].set_data([Loc[0], BLoc[0]], [Loc[1], BLoc[1]])
        self.Plots[1].set_position(self.TextLocation)
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
    def Label(self):
        return PinLabel(self.Parent.PinLabelRule, self.Index, self.Name)
    @property
    def PinBaseLocation(self):
        return self.Parent.Location + RotateOffset(self.PinBaseOffset, self.Rotation)
    @property
    def TextLocation(self):
        return self.Parent.Location + RotateOffset(self.TextBaseOffset, self.Rotation)
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
        return f"{self.Parent.CName} {self.CName}" + self.Label

class InputPinC(ComponentPinC):
    CName = "Input Pin"
    LibRef = "IPin"
    @property
    def TriggersParent(self):
        return True

class OutputPinC(ComponentPinC):
    CName = "Output Pin"
    LibRef = "OPin"
    @property
    def Level(self):
        return self.Group.Level
    @Level.setter
    def Level(self, Level):
        self.Group.SetLevel(Level, self)

def PinLabel(PinLabelRule, Index, Name):
    s = ""
    if PinLabelRule & 0b1 and not Index is None:
        s += str(Index)
    if PinLabelRule & 0b10 and Name:
        if s:
            s += f" ({Name})"
        else:
            s += Name
    return s
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

class WireC(ComponentBase):
    DefaultLinewidth = Params.GUI.PlotsWidths.Wire
    DefaultMarkersize = 0
    CName = "Wire"
    def __init__(self, Location, Rotation, WireParent=None):
        super().__init__(Location, Rotation)
        self.StoredAttribute('BuildMode', self.__class__.BuildMode)

        self.Start()
        if WireParent is None:
            self.WireChild = self.__class__(Location, Rotation, self) 
            self.WireParent = None
        else:
            self.WireChild = None
            self.WireParent = WireParent

    def SetBuildMode(self, mode):
        self.BuildMode = mode
        self.UpdateLocation()

    def PlotInit(self):
        Color, Alpha = self.Color, self.Alpha
        self.plot(self.Location[:,0], self.Location[:,1], color = Color, linestyle = Params.GUI.PlotsStyles.Wire, linewidth = self.DefaultLinewidth, alpha = Alpha)

    @property
    def Location(self):
        return self._Location
    @Location.setter
    def Location(self, Location):
        self._Location = np.zeros((2,2), dtype = int)
        self._Location[:,:] = np.array(Location)

    @property 
    def Children(self): # Children is now a property. Allows to dynamicaly discard the child wire, and to avoid registering it if not CanFix
        if not self.State.Building or self.WireChild is None or not self.WireChild.CanFix:
            return set() # Returning a set for now, to match other components
        return {self.WireChild} # 
    @Children.setter
    def Children(self, Value):
        pass
    def Fix(self):
        if not self.WireChild is None:
            if self.WireChild.CanFix:
                self.WireChild.Fix()
            else:
                self.WireChild.destroy()
        res = super().Fix()
        self.WireChild = None
        self.WireParent = None
        return res
    @property
    def AdvertisedLocations(self):
        if not self.CanFix:
            raise Exception("Asking AdvertisedLocations of a non buildable wire")
        AdvertisedLocations = []
        P1, P2 = self.Location
        A = self.StartAngle
        AdvertisedLocations.append((P1[0], P1[1], A))
        for x, y in np.linspace(P1, P2, abs(P2-P1).max()+1, dtype = int)[1:-1]:
            AdvertisedLocations.append((x,y,A))
            AdvertisedLocations.append((x,y,(A+4)%8))
        AdvertisedLocations.append((P2[0], P2[1], (A+4)%8))
        return np.array(AdvertisedLocations)
    @property
    def AdvertisedConnexions(self):
        return self.Location

    def UpdateLocation(self): # Parent takes care of moving child for building
        if self.WireChild is None:
            return
        P1 = self.Location[0,:]
        P3 = self.WireChild.Location[1,:]
        if self.BuildMode == 0: # Straight wires
            if (self.Rotation & 0b1) == 0:
                P2 = np.array([P3[0], P1[1]])
            else:
                P2 = np.array([P1[0], P3[1]])
        else:
            Offsets = P3 - P1
            Lengths = abs(Offsets)
            StraightAxis = Lengths.argmax()
            SignStraight = np.sign(Offsets[StraightAxis])
            Offsets[1-StraightAxis] = 0
            Offsets[StraightAxis] -= SignStraight * Lengths.min()
            if (self.Rotation & 0b1) == 0:
                P2 = P1 + Offsets
            else:
                P2 = P3 - Offsets
        if (P2 == P1).all():  # If WireParent has 0 length, and WireChild can be built
            P2 = np.array(P3) # We forcefully make the child be the null segment
        self.Location[1,:] = P2
        self.WireChild.Location[0,:] = P2
        
        self.UpdatePlot()
        self.WireChild.UpdatePlot()

    def Extend(self, Wire): # Assumes that all previous checks have been made. Wire is a colinear wire starting at the same location as self. Must ensure to keep self.StartAngle unchanged
        S1, E1 = self.Location
        S2, E2 = Wire.Location
        if (S1==S2).all(): # E1 must be kept
            self.Location[0,:] = E2
        elif (E1==E2).all(): # S1 must be kept
            self.Location[1,:] = S2
        elif (S1==E2).all(): # E1 must be kept
            self.Location[0,:] = S2
        elif (E1==S2).all(): # S1 must be kept
            self.Location[1,:] = E2
        else:
            LogError(f"Wrong locations while extending {self} and {Wire}")
        self.UpdatePlot()

    def UpdatePlot(self):
        self.Plots[0].set_data(self.Location[:,0], self.Location[:,1])

    @property
    def StartAngle(self):
        Offset = self.Location[1,:] - self.Location[0,:]
        if Offset[1] == 0:
            A = 0
        elif Offset[0] == Offset[1]:
            A = 1
        elif Offset[0] == 0:
            A= 2
        else:
            A = 3
        if Offset[1] < 0 or (Offset[1] == 0 and Offset[0] < 0):
            return A + 4
        else:
            return A

    def Drag(self, Cursor):
        self.WireChild.Location[1,:] = Cursor
        self.UpdateLocation()

    @property
    def CanFix(self):
        return (self.Location[0,:] != self.Location[1,:]).any()

class ConnexionC(ComponentBase):
    CName = "Connexion"
    LibRef = "Connexion"
    DefaultLinewidth = 0
    DefaultMarkersize = Params.GUI.PlotsWidths.Connexion
    def __init__(self, Location, Column):
        super().__init__(Location)
        self.StoredAttribute('Column', np.array(Column[:8]))

        self.Start()
        self.State = States.Fixed

    def PlotInit(self):
        Color, Alpha = self.Color, self.Alpha
        self.plot(self.Location[0], self.Location[1], Highlight = False, marker = Params.GUI.PlotsStyles.Connexion, markersize = self.DefaultMarkersize, color = Color, alpha = self.Alpha)

    def UpdateColumn(self, Column):
        if Column[-1] != self.ID:
            LogError(f"{self} not properly mapped, as advertised connexion ID is {Column[-1]}")
        self.Column = np.array(Column[:8])
        self.UpdateStyle()

    @property
    def IDs(self):
        IDs = set(self.Column)
        IDs.discard(0)
        return IDs
    @property
    def NWires(self):
        return (self.Column > 0).sum()

    @property
    def Alpha(self):
        if self.NWires < 3:
            return 0
        return self.State.Alpha
    @property
    def CanBeRemoved(self):
        return (self.NWires == 2 * len(self.IDs))
    @property
    def ShouldBeRemoved(self):
        IDs = self.IDs
        if len(IDs) == 0: # If nothing is left
            return True
        if len(IDs) >= 2: # If several components are here, this connexion still makes sense
            return False
        if self.NWires == 2: # One ID, 2 wires -> Onto a single wire, must auto remove. Might be an issue if we set mires middle point as a default connexion
            return True
        # Some situations may be unchecked here. Possibly add check self.Location in set(self.Links).pop().AdvertisedConnexions
        return False
    @property
    def ShouldMergeWires(self):
        if self.NWires != 2 or len(self.IDs) != 2:
            return False
        for LinkedComponent in self.Links:
            if not isinstance(LinkedComponent, WireC):
                return False
        Links = set(self.Links)
        return Links.pop().StartAngle%4 == Links.pop().StartAngle%4 # Ugly but works, should not always be true

    @property
    def AdvertisedLocations(self):
        return np.array([[self.Location[0], self.Location[1], -1]])
    def __repr__(self):
        return f"{self.CName} ({self.ID}) @ {self.Location}"

import pickle
import os
import re

import Components as ComponentsModule
import Circuit as CircuitModule
import Board as BoardModule
from Storage import StorageItem

from Values import Params
import DefaultLibrary

class BaseLibraryC:
    def __init__(self):
        self.Elements = {}
    def Advertise(self, Class):
        self.Elements[Class.LibRef] = Class
    def __getitem__(self, key):
        return self.Elements[key]

BaseLibrary = BaseLibraryC()
BaseLibrary.Advertise(ComponentsModule.ConnexionC)
BaseLibrary.Advertise(ComponentsModule.CasingPinC)
BaseLibrary.Advertise(ComponentsModule.InputPinC)
BaseLibrary.Advertise(ComponentsModule.OutputPinC)
BaseLibrary.Advertise(ComponentsModule.BoardPinC)
BaseLibrary.Advertise(ComponentsModule.StatesC)
for State in ComponentsModule.States.States:
    BaseLibrary.Advertise(State.__class__)
BaseLibrary.Advertise(CircuitModule.GroupC)
BaseLibrary.Advertise(CircuitModule.CasingGroupC)
BaseLibrary.Advertise(CircuitModule.ComponentsHandlerC)
BaseLibrary.Advertise(BoardModule.TruthTableC)
BaseLibrary.Advertise(BoardModule.BoardGroupsHandlerC)

class LibraryC:
    _extension = '.lbr'
    Folder = Params.GUI.DataAbsPath + Params.GUI.DataSubFolders['Libraries']
    @classmethod
    def NameToFile(cls, LibName):
        LibName = re.sub(r'\W+', '', LibName)
        return re.sub(r'\W+', '', LibName).lower() + cls._extension
    @classmethod
    def New(cls, LibName):
        if LibName in cls.List():
            raise Exception("Library name already taken")
        Filename = cls.NameToFile(LibName)
        with open(cls.Folder + Filename, 'wb') as f:
            f.write(pickle.dumps({'name':LibName, 'components':set()}))
        return cls(LibName)
    @classmethod
    def List(cls):
        Libraries = []
        for Filename in os.listdir(cls.Folder):
            with open(cls.Folder + Filename, 'rb') as f:
                Libraries.append(pickle.load(f)['name'])
        return sorted(Libraries)
    def __init__(self, LibName):
        self.Filename = self.NameToFile(LibName)
        with open(self.Folder + self.Filename, 'rb') as f:
            D = pickle.load(f)
        self.Name = D['name']
        self.Components = D['components']

class LibraryHanderC:
    ComponentBase = ComponentsModule.ComponentBase # Used to transmit Ax reference
    def __init__(self):
        StorageItem.GeneralLibrary = self

        self.Books = []
        self.AddBook(BookC('Standard', DefaultLibrary.Definitions))
        self.Wire = ComponentsModule.WireC

    def AddBook(self, Book):
        setattr(self, Book.Name, Book)
        self.Books.append(Book.Name)

    def IsWire(self, C): # Checks if class or class instance
        return C == ComponentsModule.WireC or isinstance(C, ComponentsModule.WireC)
    def IsBoardPin(self, C): # Checks if class or class instance
        return C == ComponentsModule.BoardPinC or isinstance(C, ComponentsModule.BoardPinC)
    def IsGroup(self, C):
        return isinstance(C, GroupC)

    def __getitem__(self, LibRef):
        if '.' in LibRef:
            BName, CName = LibRef.split('.')
            return getattr(getattr(self, BName), CName)
        else:
            return BaseLibrary[LibRef]

# Component template signature :
# (InputPins, OutputPins, Callback, Board, ForceWidth, ForceHeight, PinLabelRule, Symbol)

class BookC:
    def __init__(self, Name, BookComponents = {}):
        self.Name = Name
        self.Components = []
        for CompName, (CompData, ControlKey) in BookComponents.items():
            if hasattr(self, CompName):
                LogWarning(f"Component name {CompName} already exists in this book")
                continue
            self.Components.append(CompName)
            if isinstance(CompData, type(ComponentsModule.ComponentBase)):
                CompClass = CompData
                CompClass.Book = self
            else:
                CompClass = self.CreateComponentClass(CompName, CompData)
                if CompClass is None:
                    continue
            setattr(self, CompName, CompClass)
            setattr(self, 'key_'+CompName, ControlKey)
    def __repr__(self):
        return self.Name

    def CreateComponentClass(self, CompName, CompData):
        try:
            InputPinsDef, OutputPinsDef, Callback, UndefRun, Board, ForceWidth, ForceHeight, PinLabelRule, Symbol = CompData
            PinIDs = set()
            for PinLocation, PinName in InputPinsDef + OutputPinsDef:
                if PinLocation in PinIDs:
                    raise ValueError
        except ValueError:
            LogWarning(f"Unable to load component {CompName} from its definition")
            return
        return type(CompName,
                    (ComponentsModule.CasedComponentC, ),
                    {
                        #'__init__': Components.CasedComponentC.__init__,
                        'CName': CompName,
                        'Book': self.Name,
                        'InputPinsDef'    : InputPinsDef,
                        'OutputPinsDef'    : OutputPinsDef,
                        'Callback'   : Callback,
                        'UndefRun'   : UndefRun,
                        'Board' : Board,
                        'ForceWidth' : ForceWidth,
                        'ForceHeight': ForceHeight,
                        'PinLabelRule':PinLabelRule,
                        'Symbol':Symbol,
                    })

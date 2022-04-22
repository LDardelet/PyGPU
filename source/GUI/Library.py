import os
import re

import Components as ComponentsModule
import Circuit as CircuitModule
import Board as BoardModule
from Storage import StorageItem, FileSavedEntityC

from Values import Params
import DefaultLibrary

class HiddenBookC:
    def __init__(self):
        self.Elements = {}
    def Advertise(self, Class):
        self.Elements[Class.LibRef] = Class
    def __getitem__(self, key):
        return self.Elements[key]

# Component template signature :
# ('InputPins', 'OutputPins', Callback, Board, ForceWidth, ForceHeight, PinLabelRule, Symbol)

class BookC:
    def __init__(self, Name, CList, CDicts):
        self.Name = Name
        self.CList = CList
        self.CDicts = CDicts

        self.CreateComponentsClasses()

    def CreateComponentsClasses(self):
        self.CClasses = {}
        for CName, CDict in self.CDicts.items():
            if CName in self:
                LogWarning(f"Component name {CName} already exists in this book")
                continue
            if isinstance(CDict, type(ComponentsModule.ComponentBase)): # Happens for Standard library, for Wire and Board pin
                CClass = CDict
                CClass.Book = self.Name
            else:
                CClass = self.CreateComponentClass(CName, CDict, self.Name)
                if CClass is None:
                    LogWarning(f"{self} unable to load {CName} from its definition")
                    continue
            self.CClasses[CName] = CClass
    
    @staticmethod
    def CreateComponentClass(CName, CDict, BookName):
        CDict['Book'] = BookName
        CDict['CName'] = CName
        try:
            PinIDs = set()
            for PinLocation, PinName in CDict['InputPinsDef'] + CDict['OutputPinsDef']:
                if PinLocation in PinIDs:
                    raise ValueError
                PinIDs.add(PinLocation)
        except ValueError:
            return
        return type(CName,
                    (ComponentsModule.CasedComponentC, ),
                    CDict)
    def __contains__(self, CName):
        return CName in self.CClasses
    def __repr__(self):
        return f"{self.Name} components book"

class CustomBookC(FileSavedEntityC, BookC):
    LibRef = "CustomBookC"
    _extension = '.book'
    Folder = Params.GUI.DataAbsPath + Params.GUI.DataSubFolders['Library']
    @classmethod
    def NameToFile(cls, BookName):
        BookName = re.sub(r'\W+', '', BookName)
        return cls.Folder + re.sub(r'\W+', '', BookName).lower() + cls._extension
    @classmethod
    def New(cls, BookName):
        if BookName in cls.List():
            raise ValueError(f"Book name {BookName} already taken")
        return cls(BookName, New = True)
    @classmethod
    def List(cls):
        Books = []
        for Filename in os.listdir(cls.Folder):
            if cls.IsBook(Filename):
                Books.append(FileSavedEntityC.PeekFile(cls.Folder + Filename, {'Name'})['Name'][1])
        return sorted(Books)
    @classmethod
    def IsBook(cls, Filename):
        return Filename[-len(cls._extension):] == cls._extension
    def __init__(self, BookName, New = False):
        self.StoredAttribute('Name', BookName)
        self.StoredAttribute('CDicts', {})
        self.StoredAttribute('CList', [])
        self.Filename = self.NameToFile(BookName)

        if not New:
            FileSavedEntityC.Load(self)

        self.CreateComponentsClasses()

    def AddComponent(self, CDict):
        CName = CDict['CName']
        if CName in self:
            print(f"Overwriting {CName}")
            self.CList.remove(CName)
        self.CDicts[CName] = CDict
        self.CList.append(CName)
        FileSavedEntityC.Save(self)
        self.CClasses[CName] = self.CreateComponentClass(CName, CDict, self)
        print(f"Added {CName} to {self}")

StandardBook = BookC(DefaultLibrary.Name, DefaultLibrary.CList, DefaultLibrary.CDicts)

class LibraryHandlerC:
    ComponentBase = ComponentsModule.ComponentBase # Used to transmit Ax reference
    Folder = Params.GUI.DataAbsPath + Params.GUI.DataSubFolders['Library']
    DefaultProfile = 'Default'
    _extension = '.lbr'
    _CurrentStr = '**'
    def __init__(self):
        StorageItem.GeneralLibrary = self
        self.Wire = ComponentsModule.WireC
        self.BoardPin = ComponentsModule.BoardPinC

    def Load(self, Profile):
        self.Profile = Profile
        self.Books = {StandardBook.Name : StandardBook}
        self.BooksList = [StandardBook.Name]

        if not self.ProfileExists(Profile):
            self.NewProfile(Profile)
            self.SaveCurrentProfile()
        else:
            print(f"Loading library profile {self.Profile}")

        with open(self.NameToFile(self.Profile), 'r') as f:
            Lines = f.readlines()
        ReadProfile = Lines.pop(0).strip().strip(self._CurrentStr)
        if ReadProfile != self.Profile:
            print(len(ReadProfile), len(self.Profile))
            print(f"Corrupted profile ({ReadProfile} vs {self.Profile})")
        MissingBook = False
        ExistingBooks = CustomBookC.List()
        for BookName in Lines:
            if BookName not in ExistingBooks:
                print(f'Missing book : {BookName}')
                MissingBook = True
                continue
            self.Books[BookName] = CustomBookC(BookName)
            self.BooksList.append(BookName)
        
        if MissingBook:
            self.SaveCurrentProfile()
    
    @classmethod
    def ProfileExists(cls, Profile):
        return Profile in cls.List()[0]
    @classmethod
    def List(cls):
        Profiles = []
        CurrentProfile = None
        for Filename in os.listdir(cls.Folder):
            if not cls.IsProfile(Filename):
                continue
            with open(cls.Folder + Filename, 'r') as f:
                Profile = f.readlines()[0].strip()
            if Profile[:len(cls._CurrentStr)] == cls._CurrentStr:
                Profile = Profile[len(cls._CurrentStr):]
                CurrentProfile = Profile
            Profiles.append(Profile)
        return sorted(Profiles), CurrentProfile
    @classmethod
    def NewProfile(cls, Profile):
        print(f"Creating new library profile {Profile}")
        with open(cls.NameToFile(Profile), 'w') as f:
            f.writelines([Profile])
        return Profile
    @classmethod
    def NameToFile(cls, Profile):
        Profile = re.sub(r'\W+', '', Profile)
        return cls.Folder + re.sub(r'\W+', '', Profile).lower() + cls._extension
    @classmethod
    def IsProfile(cls, Filename):
        return Filename[-len(cls._extension):] == cls._extension

    def AddBook(self, Book):
        self.Books[Book.Name] = Book
        self.BooksList.append(Book.Name)
        self.SaveCurrentProfile()
        print(f"Added {Book} to profile {self.Profile}")

    def SaveCurrentProfile(self):
        Data = [f"{self._CurrentStr}{self.Profile}"]
        for BookName in self.BooksList[1:]:
            Data.append(f"{BookName}")
        with open(self.NameToFile(self.Profile), 'w') as f:
            f.write('\n'.join(Data))

    def IsWire(self, C): # Checks if class or class instance
        return C == self.Wire or isinstance(C, self.Wire)
    def IsBoardPin(self, C): # Checks if class or class instance
        return C == self.BoardPin or isinstance(C, self.BoardPin)
    def IsGroup(self, C):
        return isinstance(C, GroupC)

    def __contains__(self, Book):
        return Book.Name in self.BooksList

    def __getitem__(self, LibRef):
        if '.' in LibRef:
            BName, CName = LibRef.split('.')
            return self.Books[BName].CClasses[CName]
        else:
            return HiddenBook[LibRef]

HiddenBook = HiddenBookC()
HiddenBook.Advertise(ComponentsModule.ConnexionC)
HiddenBook.Advertise(ComponentsModule.CasingPinC)
HiddenBook.Advertise(ComponentsModule.InputPinC)
HiddenBook.Advertise(ComponentsModule.OutputPinC)
HiddenBook.Advertise(ComponentsModule.BoardPinC)
HiddenBook.Advertise(ComponentsModule.StatesC)
for State in ComponentsModule.States.States:
    HiddenBook.Advertise(State.__class__)
HiddenBook.Advertise(CircuitModule.GroupC)
HiddenBook.Advertise(CircuitModule.CasingGroupC)
HiddenBook.Advertise(CircuitModule.ComponentsHandlerC)
HiddenBook.Advertise(BoardModule.BoardC)
HiddenBook.Advertise(BoardModule.TruthTableC)
HiddenBook.Advertise(BoardModule.BoardGroupsHandlerC)
HiddenBook.Advertise(CustomBookC)

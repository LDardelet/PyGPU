import numpy as np
import json
import os

from Console import Log, LogSuccess, LogWarning

class FileHandler:
    def __init__(self):
        self.Filename = None
    
    def Load(self, Filename): # Only loads data from file to memory
        self.Filename = Filename
        if Filename is None:
            self.Data = {'handler':None}
        else:
            with open(Filename) as f:
                return EntryPoint().Load(json.load(f))

    def Save(self, **kwargs):
        if self.Filename is None:
            raise FileNotFoundError("Must specify a filename to save data")

        Data = EntryPoint(**kwargs).Store()
        print(Data)

        with open(self.Filename, 'w') as f:
            json.dump(Data, f)
            LogSuccess("Data saved")

    def __getitem__(self, key):
        return self.Data[key]

STORAGE = 0
BUILDIN = 1
ARRAY = 2
SET = 3
DICT = 4
LIST = 5
TUPLE = 6
REFERENCE = 7

class StorageItem:
    Library = None
    Packed = {}
    MaxID = 0
    Unpacked = {}
    def __init__(self, Data = None):
        self._StoredAttributes = {'_StoredAttributes', 'LibRef'}
        if not Data is None:
            self.Load(Data)

    def OnLoad(self):
        pass

    @classmethod
    def StartPacking(cls):
        cls.Packed = {}
        MaxID = 0
    @classmethod
    def NewID(cls):
        cls.MaxID += 1
        return cls.MaxID
    @classmethod
    def StartUnpacking(cls):
        cls.Unpacked = {}

    def Store(self, EntryPoint = False):
        if EntryPoint:
            self.StartPacking()
        D = {}
        for Key in self._StoredAttributes:
            D[Key] = self.Pack(getattr(self, Key))
        return D

    def Load(self, D):
        for Key, Data in D.items():
            setattr(self, Key, self.Unpack(*Data))

    def Pack(self, Value):
        if isinstance(Value, StorageItem):
            if Value in self.Packed:
                return (REFERENCE, self.Packed[Value])
            else:
                ID = self.NewID()
                self.Packed[Value] = ID
                return (STORAGE, (Value.Store(), ID))
        VType = type(Value)
        if VType == dict:
            return (DICT, {VKey:self.Pack(VValue) for VKey, VValue in Value.items()})
        elif VType == tuple:
            return (TUPLE, tuple([self.Pack(VValue) for VValue in Value]))
        elif VType == list:
            return (LIST, [self.Pack(VValue) for VValue in Value])
        elif VType == set:
            return (SET, [self.Pack(VValue) for VValue in Value])
        elif VType == np.ndarray:
            return (ARRAY, [self.Pack(VValue) for VValue in Value.tolist()])
        else:
            return (BUILDIN, Value)
    
    def Unpack(self, Type, Value):
        print(Type, Value)
        if Type == STORAGE:
            Value, ID = Value
            print(Value['LibRef'][1])
            NewStorage = StorageItem.Library[Value.pop('LibRef')[1]]()
            NewStorage.Load(Value)
            self.Unpacked[ID] = NewStorage
            return NewStorage
        elif Type == REFERENCE:
            return self.Unpacked[Value]
        elif Type == DICT:
            return {VKey:self.Unpack(*VValue) for VKey, VValue in Value.items()}
        elif Type == TUPLE:
            return tuple([self.Unpack(*VValue) for VValue in Value])
        elif Type == LIST:
            return [self.Unpack(*VValue) for VValue in Value]
        elif Type == SET:
            return set([self.Unpack(*VValue) for VValue in Value])
        elif Type == ARRAY:
            return np.array([self.Unpack(*VValue) for VValue in Value])
        elif Type == BUILDIN:
            return Value
        else:
            raise ValueError(f"Type {Type} saved for value {Value}")

    @property
    def LibRef(self):
        return str(self.__class__).split('.')[-1]

class EntryPoint(StorageItem):
    def __init__(self, **kwargs):
        StorageItem.__init__(self)
        for Key, Value in kwargs.items():
            setattr(self, Key, Value)
            self._StoredAttributes.add(Key)
    def Store(self):
        return StorageItem.Store(self, EntryPoint = True)
    def Load(self, D):
        self.StartUnpacking()
        StoredData = {}
        for Key, Data in D.items():
            StoredData[Key] = self.Unpack(*Data)
        for Storage in self.Unpacked.values():
            Storage.OnLoad()
        return StoredData

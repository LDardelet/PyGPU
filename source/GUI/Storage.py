import numpy as np
import pickle
import os
import re

from Console import Log, LogSuccess, LogWarning

BUILDIN = 1
ARRAY = 2
SET = 3
DICT = 4
LIST = 5
TUPLE = 6
REFERENCE = 7

class Meta(type):
    # This metaclass allows every storage item to start their init from StorageItem.__init__
    # This method decides if it is a regular instanciation, or data from loaded values, and calls the corresponding methods.
    def __call__(cls, *args, **kwargs):
        self = cls.__new__(cls, *args, **kwargs)
        if 'UnpackData' in kwargs:
            self.Unpack(*kwargs['UnpackData'])
        else:
            StorageItem.__init__(self, *args, **kwargs)
            if isinstance(self, FileSavedEntityC):
                FileSavedEntityC.__init__(self, *args, **kwargs)
            self.__init__(*args, **kwargs) # Start method can be called when necessary in the __init__
        return self

class StorageItem(metaclass = Meta):
    GeneralLibrary = None
    LibRef = None
    _StorageLog = False
    _StoreTmpAttributes = False
    def __init__(self, *args, **kwargs):
        # If we reach this point, it means that no loaded data was found in kwargs. We start by initializing the element as a StorageItem, and fall back to the regular behaviour
        if hasattr(self, '_SA'): # Stops any infinite loop for all non-overloaded __init__ inherited classes
            return
        self.Log("Starting _SA", self.__class__)
        self._SA = {'_SA', 'LibRef', '_StoreTmpAttributes'}
        self._Saved = True
        if self._StoreTmpAttributes:
            self.StoredAttribute('_TA', {})

    def Log(self, *args, **kwargs):
        if not self._StorageLog:
            return
        Log(*args, **kwargs)
    def StoredAttribute(self, attr, defaultValue):
        self._SA.add(attr)
        if hasattr(self, attr) and not hasattr(self.__class__, attr):
            LogWarning(f"Weird : attribute {attr} already set while loading")
        setattr(self, attr, defaultValue)
    def TmpAttribute(self, attr, defaultValue):
        if not self._StoreTmpAttributes:
            raise Exception("Storing of temporary attributes is disabled")
        self._TA[attr] = type(defaultValue)(defaultValue) # Dereferenciation to ensure default value is saved
        if hasattr(self, attr):
            LogWarning(f"Weird : temporary attribute {attr} already set")
        setattr(self, attr, defaultValue)

    def Start(self):
        # Method to start a components dynamical data after load. Possibly can be used as __init__ finish.
        pass

    def Store(self, IDsToDicts, Packed):
        D = {}
        for Key in self._SA:
            D[Key] = self.Pack(getattr(self, Key), IDsToDicts, Packed)
        return D

    def Pack(self, Value, IDsToDicts, Packed, NewItem = False, LogTab = 0):
        IterableTab = 1
        NewObjectTab = 2
        if NewItem:
            D = {}
            if self.LibRef is None:
                raise ValueError(f"Unassigned LibRef for {self}")
            for Key in self._SA:
                self.Log(f"Saving data in {Key}", LogTab+IterableTab)
                D[self.Pack(Key, IDsToDicts, Packed, False, LogTab+IterableTab)] = self.Pack(getattr(self, Key), IDsToDicts, Packed, False, LogTab+IterableTab)
            if self._StoreTmpAttributes:
                for Key, DefaultValue in self._TA.items():
                    self.Log(f"Saving default attribute {Key}", LogTab)
                    D[Key] = self.Pack(DefaultValue, IDsToDicts, Packed, False, LogTab+IterableTab) # Class is reinstanciated with the default value
            return D
        if isinstance(Value, StorageItem):
            if Value in Packed:
                ID = Packed[Value]
                self.Log(f"Referenced object as ID {ID}", LogTab)
            else:
                ID = max(Packed.values()) + 1
                Packed[Value] = ID
                self.Log(f"Packing object {Value} as ID {ID}", LogTab)
                IDsToDicts[ID] = Value.Pack(None, IDsToDicts, Packed, True, LogTab+NewObjectTab)
            return (REFERENCE, ID)
        VType = type(Value)
        if VType == dict:
            return (DICT, {self.Pack(VKey, IDsToDicts, Packed, False, LogTab+IterableTab):self.Pack(VValue, IDsToDicts, Packed, False, LogTab+IterableTab) for VKey, VValue in Value.items()})
        elif VType == tuple:
            return (TUPLE, tuple([self.Pack(VValue, IDsToDicts, Packed, False, LogTab+IterableTab) for VValue in Value]))
        elif VType == list:
            return (LIST, [self.Pack(VValue, IDsToDicts, Packed, False, LogTab+IterableTab) for VValue in Value])
        elif VType == set:
            return (SET, [self.Pack(VValue, IDsToDicts, Packed, False, LogTab+IterableTab) for VValue in Value])
        elif VType == np.ndarray:
            return (ARRAY, Value)
        else:
            return (BUILDIN, Value)

    def Unpack(self, Type, Value, IDsToDicts, Unpacked, NewItem = False, LogTab = 0, KeyName = ''):
        IterableTab = 1
        NewObjectTab = 2
        if NewItem:
            ID = Type
            Unpacked[ID] = self
            self._Saved = True
            for Key, Data in Value.items():
                setattr(self, self.Unpack(*Key, IDsToDicts, Unpacked, False, LogTab+NewObjectTab, Key), self.Unpack(*Data, IDsToDicts, Unpacked, False, LogTab+NewObjectTab, Key))
            for Key in self._SA:
                if not hasattr(self, Key):
                    LogWarning(f"Object {self.LibRef} ({self}) missing stored attribute {Key}")
            self.Log(f"Unpacked new object {self.LibRef} with ID {ID}", LogTab)
            return
        if Type in (DICT, LIST, SET, TUPLE, ARRAY) and False:
            self.Log(bool(KeyName)*f"{KeyName}: " + f"Unpacking {len(Value)}-items iterable", LogTab)
        if Type == REFERENCE:
            ID = Value
            if ID in Unpacked:
                self.Log(bool(KeyName)*f"{KeyName}: " + f"Referenced from object {ID}", LogTab)
                return Unpacked[ID]
            else:
                Value = IDsToDicts[ID]
                LibRef = Value.pop((BUILDIN, 'LibRef'))[1]
                self.Log(bool(KeyName)*f"{KeyName}: " + f"Unpacking new object {ID} from LibRef {LibRef}", LogTab)
                
                if LibRef is None:
                    raise ValueError("LibRef unassigned")
                StoredItemClass = StorageItem.GeneralLibrary[LibRef]
                StoredItemClass(UnpackData = (ID, Value, IDsToDicts, Unpacked, True, LogTab))
                return Unpacked[ID]
        elif Type == DICT:
            return {self.Unpack(*VKey, IDsToDicts, Unpacked, False, LogTab+IterableTab, f"{VKey}(key)"):self.Unpack(*VValue, IDsToDicts, Unpacked, False, LogTab+IterableTab, VKey) for VKey, VValue in Value.items()}
        elif Type == TUPLE:
            return tuple([self.Unpack(*VValue, IDsToDicts, Unpacked, False, LogTab+IterableTab) for VValue in Value])
        elif Type == LIST:
            return [self.Unpack(*VValue, IDsToDicts, Unpacked, False, LogTab+IterableTab) for VValue in Value]
        elif Type == SET:
            return set([self.Unpack(*VValue, IDsToDicts, Unpacked, False, LogTab+IterableTab) for VValue in Value])
        elif Type == ARRAY:
            return Value
        elif Type == BUILDIN:
            return Value
        else:
            raise ValueError(bool(Key)*f"{Key}: " + f"Type {Type} saved for value {Value}")

class FileSavedEntityC(StorageItem):
    def __init__(self, *args, **kwargs):
        self.StoredAttribute('Filename', None)
    def Save(self):
        Objects = {}
        D = self.Pack(None, Objects, {None:0}, NewItem = True)
        D['_obj'] = Objects
        Saved = False
        with open(self.Filename, 'wb') as f:
            f.write(pickle.dumps(D))
            Saved = True
            for Item in self._SA:
                if isinstance(Item, StorageItem):
                    Item.Saved = True
        return Saved
    def Load(self):
        with open(self.Filename, 'rb') as f:
            self._RawData = pickle.load(f)
        print("Start loading data")
        Base = dict(self._RawData)
        IDsToDicts = Base.pop('_obj')
        Unpacked = {}
        
        StoredData = self.Unpack(DICT, Base, IDsToDicts, Unpacked, NewItem = False)
        for ID, Object in Unpacked.items():
            #print(f"Starting object {ID}: {Object}")
            try:
                Object.Start()
            except:
                print(" - Failed start of {Object}")
                return False
        for Item in self._SA:
            try:
                setattr(self, Item, StoredData.pop(Item))
            except KeyError:
                print(f"Leaving default value for {Item}")
        if StoredData:
            print("Non recovered items:\n - "+'\n - '.join([str(Key) for Key in StoredData.keys()]))
        return True
    @classmethod
    def PeekFile(cls, Filename, Keys):
        Data = {}
        with open(Filename, 'rb') as f:
            RawData = pickle.load(f)
            for Key in Keys:
                Data[Key] = RawData[(BUILDIN, Key)]
        return Data

def Log(data, LogTab = 0, Tab = 2):
    print(LogTab*Tab*' '+data)

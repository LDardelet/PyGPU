import numpy as np
import pickle
import os
import re

from Console import Log, LogSuccess, LogWarning

class FileHandlerC:
    def __init__(self):
        self.Filename = None
        self.LoadedData = None
    
    def Load(self, Filename): # Only loads data from file to memory
        self.Filename = Filename
        with open(Filename, 'rb') as f:
            self.LoadedData = EntryPoint().StartUnpack(pickle.load(f))
        return self.LoadedData

    def Save(self, **kwargs):
        if self.Filename is None:
            raise FileNotFoundError("Must specify a filename to save data")

        Data = EntryPoint(**kwargs).StartPack()
        with open(self.Filename, 'wb') as f:
            f.write(pickle.dumps(Data))
            LogSuccess("Data saved")

    def __getitem__(self, key):
        return self.Data[key]

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
        return self

class StorageItem(metaclass = Meta):
    Library = None
    LibRef = None
    _StoreTmpAttributes = False
    def __init__(self, *args, **kwargs):
        # If we reach this point, it means that no loaded data was found in kwargs. We start by initializing the element as a StorageItem, and fall back to the regular behaviour
        if hasattr(self, '_SA'): # Stops any infinite loop for all non-overloaded __init__ inherited classes
            return
        self._SA = {'_SA', 'LibRef', '_StoreTmpAttributes'}
        self._Modified = False
        if self._StoreTmpAttributes:
            self.StoredAttribute('_TA', {})
        self.__init__(*args, **kwargs) # Start method if left to be called when necessary in the __init__
    def StoredAttribute(self, attr, defaultValue):
        self._SA.add(attr)
        if hasattr(self, attr) and not hasattr(self.__class__, attr):
            print(f"Weird : attribute {attr} already set while loading")
        setattr(self, attr, defaultValue)
    def TmpAttribute(self, attr, defaultValue):
        if not self._StoreTmpAttributes:
            raise Exception("Storing of temporary attributes is disabled")
        self._TA[attr] = type(defaultValue)(defaultValue) # Dereferenciation to ensure default value is saved
        if hasattr(self, attr):
            print(f"Weird : temporary attribute {attr} already set")
        setattr(self, attr, defaultValue)

    def Start(self):
        # Method to start a components dynamical data after load. Possibly can be used as __init__ finish.
        pass

    def Store(self, IDsToDicts, Packed):
        D = {}
        for Key in self._SA:
            D[Key] = self.Pack(getattr(self, Key), IDsToDicts, Packed)
        return D

    def Pack(self, Value, IDsToDicts, Packed, NewItem = False):
        if NewItem:
            D = {}
            for Key in self._SA:
                print(f"Saving data in {Key}")
                D[Key] = self.Pack(getattr(self, Key), IDsToDicts, Packed)
            if self._StoreTmpAttributes:
                for Key, DefaultValue in self._TA.items():
                    print(f"Saving default attribute {Key}")
                    D[Key] = self.Pack(DefaultValue, IDsToDicts, Packed) # Class is reinstanciated with the default value
            self._Modified = False
            return D
        if isinstance(Value, StorageItem):
            if Value in Packed:
                ID = Packed[Value]
            else:
                ID = max(Packed.values()) + 1
                Packed[Value] = ID
                print(f"Packed object {Value} as ID {ID}")
                IDsToDicts[ID] = Value.Pack(None, IDsToDicts, Packed, NewItem = True)
            return (REFERENCE, ID)
        VType = type(Value)
        if VType == dict:
            return (DICT, {VKey:self.Pack(VValue, IDsToDicts, Packed) for VKey, VValue in Value.items()})
        elif VType == tuple:
            return (TUPLE, tuple([self.Pack(VValue, IDsToDicts, Packed) for VValue in Value]))
        elif VType == list:
            return (LIST, [self.Pack(VValue, IDsToDicts, Packed) for VValue in Value])
        elif VType == set:
            return (SET, [self.Pack(VValue, IDsToDicts, Packed) for VValue in Value])
        elif VType == np.ndarray: # Possible error here, if V.shape = ()
            #return (ARRAY, [self.Pack(VValue, IDsToDicts, Packed) for VValue in Value.tolist()])
            return (ARRAY, Value)
        else:
            return (BUILDIN, Value)

    def Unpack(self, Type, Value, IDsToDicts, Unpacked, NewItem = False, LogTab = 0, KeyName = ''):
        IterableTab = 1
        NewObjectTab = 2
        if NewItem:
            ID = Type
            Unpacked[ID] = self
            self._Modified = False
            #MissingAttributes = set(self._SA)
            for Key, Data in Value.items():
                setattr(self, Key, self.Unpack(*Data, IDsToDicts, Unpacked, False, LogTab+NewObjectTab, Key))
            #    if Key not in self._SA:
            #        Log(f"Loaded wrong attribute : {Key}", LogTab)
            #    else:
            #        MissingAttributes.remove(Key)
            #for Key in MissingAttributes:
            #    Log(f"Missing attribute : {Key}", LogTab)

            Log(f"Unpacked new object {self.LibRef} with ID {ID}", LogTab)
#            self.Start()
#            Log(f"{self} started", LogTab)
            return
        if Type in (DICT, LIST, SET, TUPLE, ARRAY):
            Log(bool(KeyName)*f"{KeyName}: " + f"Unpacking {len(Value)}-items iterable", LogTab)
        if Type == REFERENCE:
            ID = Value
            if ID in Unpacked:
                Log(bool(KeyName)*f"{KeyName}: " + f"Referenced from object {ID}", LogTab)
                return Unpacked[ID]
            else:
                Value = IDsToDicts[ID]
                LibRef = Value.pop('LibRef')[1]
                Log(bool(KeyName)*f"{KeyName}: " + f"Unpacking new object {ID} from LibRef {LibRef}", LogTab)
                StorageItem.Library[LibRef](UnpackData = (ID, Value, IDsToDicts, Unpacked, True, LogTab))
                #Unpacked[ID] = StorageItem.Library[Value.pop('LibRef')[1]](UnpackData = (ID, Value, IDsToDicts, Unpacked, NewItem = True, LogTab = LogTab))
                #Unpacked[ID].Unpack(DICT, Value, IDsToDicts, Unpacked, NewItem = True, LogTab = LogTab)
                return Unpacked[ID]
        elif Type == DICT:
            return {VKey:self.Unpack(*VValue, IDsToDicts, Unpacked, False, LogTab+IterableTab, VKey) for VKey, VValue in Value.items()}
        elif Type == TUPLE:
            return tuple([self.Unpack(*VValue, IDsToDicts, Unpacked, False, LogTab+IterableTab) for VValue in Value])
        elif Type == LIST:
            return [self.Unpack(*VValue, IDsToDicts, Unpacked, False, LogTab+IterableTab) for VValue in Value]
        elif Type == SET:
            return set([self.Unpack(*VValue, IDsToDicts, Unpacked, False, LogTab+IterableTab) for VValue in Value])
        elif Type == ARRAY:
            #return np.array([self.Unpack(*VValue, IDsToDicts, Unpacked, LogTab+1) for VValue in Value])
            return Value
        elif Type == BUILDIN:
            #Log(bool(KeyName)*f"{KeyName}: " + f"Unpacked {type(Value)} value {Value}", LogTab)
            return Value
        else:
            raise ValueError(bool(Key)*f"{Key}: " + f"Type {Type} saved for value {Value}")

def Log(data, LogTab = 0, Tab = 2):
    print(LogTab*Tab*' '+data)

class EntryPoint(StorageItem):
    LibRef = "EntryPoint"
    def __init__(self, **kwargs):
        for Key, Value in kwargs.items():
            setattr(self, Key, Value)
            self._SA.add(Key)
    def StartPack(self):
        Objects = {}
        D = self.Pack(None, Objects, {None:0}, NewItem = True)
        D['_obj'] = Objects
        return D
    def StartUnpack(self, D):
        print("Start loading data")
        IDsToDicts = D.pop('_obj')
        Unpacked = {}
        
        StoredData = self.Unpack(DICT, D, IDsToDicts, Unpacked, NewItem = False)
        for ID, Object in Unpacked.items():
            print(f"Starting object {ID}: {Object}")
            try:
                Object.Start()
            except:
                print("   Failed")
        return StoredData

def Modifies(func):
    def ModFunc(self, *args, **kwargs):
        self._Modified = True
        return func(self, *args, **kwargs)
    return ModFunc

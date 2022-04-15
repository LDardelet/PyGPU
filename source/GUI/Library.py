import pickle
import os
import re

from Values import Params

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

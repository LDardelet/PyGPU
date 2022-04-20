def Void(*args, **kwargs):
    pass

class PDict:
    def __init__(self, Name=''):
        self.__dict__['_Children'] = {}
        self.__dict__['_Name'] = Name
    def __getattr__(self, key):
        if key[0] == '_':
            raise AttributeError
        try:
            return self._Children[key]
        except:
            self._Children[key] = self.__class__(key)
            return self._Children[key]
    def __repr__(self):
        return '\n'.join([f"{Child}: {len(Child)} element" for Child in self._Children])
    def __setattr__(self, key, value):
        self._Children[key] = value
    def __len__(self):
        return len(self._Children)
    def __eq__(self, rhs):
        raise KeyError(self.__dict__['_Name'])

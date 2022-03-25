from Components import Wire, PinDict

def W(Index, Name = ''):
    return ((PinDict.W, Index), Name)
def E(Index, Name = ''):
    return ((PinDict.E, Index), Name)
def N(Index, Name = ''):
    return ((PinDict.N, Index), Name)
def S(Index, Name = ''):
    return ((PinDict.S, Index), Name)

Definitions = {
    'Wire' :Wire,
    'And': ([W(0),
             W(1)],
            [E(0)],
        lambda a, b: a and b, 
        None, 
        None, 
        None, 
        True,
        '&'),
    'Or' : ([W(0),
             W(1)],
            [E(0)],
        lambda a, b: a or b , 
        None, 
        None, 
        None, 
        True,
        '|'),
    'Not': ([W(0, 'in')],
            [E(0, 'out')],
        lambda a   : not a  , 
        None, 
        None, 
        1, 
        False,
        '~'),
    'High' :([],
        [E(0)],
        lambda     : True   , 
        None, 
        2   , 
        2   ,
        False,
        '1'),
    'Low':([],
        [E(0)],
        lambda     : False  , 
        None, 
        2   , 
        2   ,
        False,
        '0'),
}

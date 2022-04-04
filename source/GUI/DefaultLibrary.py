from Components import WireC, BoardPinC, PinDict

def W(Index, Name = ''):
    return ((PinDict.W, Index), Name)
def E(Index, Name = ''):
    return ((PinDict.E, Index), Name)
def N(Index, Name = ''):
    return ((PinDict.N, Index), Name)
def S(Index, Name = ''):
    return ((PinDict.S, Index), Name)

Definitions = {
    'Wire' :(WireC, 'w'),
    'I/O'  :(BoardPinC, 'i'),
    'And'  :(([W(0),
               W(1)],
              [E(0)],
        lambda a, b: (a and b,), 
        None, 
        None, 
        None, 
        0b11,
        '&'), 'a'),
    'Or' :(([W(0),
             W(1)],
            [E(0)],
        lambda a, b: (a or b,) , 
        None, 
        None, 
        None, 
        0b11,
        '|'), 'o'),
    'Not':(([W(0, 'in')],
            [E(0, 'out')],
        lambda a   : (not a,)  , 
        None, 
        None, 
        1, 
        0b10,
        '~'), 'n'),
    'High' :(([],
        [E(0)],
        lambda     : (True,)   , 
        None, 
        2   , 
        2   ,
        0b00,
        '+'),  'h'),
    'Low':(([],
        [E(0)],
        lambda     : (False,)  , 
        None, 
        2   , 
        2   ,
        0b00,
        '-'), 'l'),
}

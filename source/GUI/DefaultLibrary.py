from Components import WireC, BoardPinC, PinDict

def W(SideIndex, Name = ''):
    return ((PinDict.W, SideIndex), Name)
def E(SideIndex, Name = ''):
    return ((PinDict.E, SideIndex), Name)
def N(SideIndex, Name = ''):
    return ((PinDict.N, SideIndex), Name)
def S(SideIndex, Name = ''):
    return ((PinDict.S, SideIndex), Name)

Definitions = {
    'Wire' :(WireC, 'w'),
    'I/O'  :(BoardPinC, 'i'),
    'And'  :(([W(0),
               W(1)],
              [E(0)],
        lambda a, b: (a & b,), 
        None, 
        None, 
        None, 
        0b11,
        '&'), 'a'),
    'Or' :(([W(0),
             W(1)],
            [E(0)],
        lambda a, b: (a | b,) , 
        None, 
        None, 
        None, 
        0b11,
        '|'), 'o'),
    'XOr' :(([W(0),
             W(1)],
            [E(0)],
        lambda a, b: (a ^ b,) , 
        None, 
        None, 
        None, 
        0b11,
        '^'), 'x'),
    'Not':(([W(0, 'in')],
            [E(0, 'out')],
        lambda a   : (not a,)  , 
        None, 
        None, 
        None, 
        0b01,
        '~'), 'n'),
    'High' :(([],
        [E(0)],
        lambda     : (True,)   , 
        None, 
        None, 
        None,
        0b00,
        '+'),  'h'),
    'Low':(([],
        [E(0)],
        lambda     : (False,)  , 
        None, 
        None, 
        None,
        0b00,
        '-'), 'l'),
}

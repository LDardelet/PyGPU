from Components import WireC, BoardPinC, PinDict
from Values import Levels

def W(SideIndex, Name = ''):
    return ((PinDict.W, SideIndex), Name)
def E(SideIndex, Name = ''):
    return ((PinDict.E, SideIndex), Name)
def N(SideIndex, Name = ''):
    return ((PinDict.N, SideIndex), Name)
def S(SideIndex, Name = ''):
    return ((PinDict.S, SideIndex), Name)

Name = 'Standard'
_DefTuple = ('InputPinsDef', 'OutputPinsDef', 'Callback', 'UndefRun', 'Board', 'ForceWidth', 'ForceHeight', 'PinLabelRule', 'Symbol')
_Definitions = (
    ('Wire' ,WireC, 'w'),
    ('I/O'  ,BoardPinC, 'i'),
    ('And'  ,([W(0),
               W(1)],
              [E(0)],
              lambda a: (a & 0b1) & ((a>>1) & 0b1), 
        False,
        None, 
        None, 
        None, 
        0b00,
        '&'), 'a'),
    ('Or' ,([W(0),
             W(1)],
            [E(0)],
        lambda a: (a & 0b1) | ((a>>1) & 0b1) , # Need this to allow for undef run
        False,
        None, 
        None, 
        None, 
        0b00,
        '|'), 'o'),
    ('XOr' ,([W(0),
             W(1)],
            [E(0)],
        lambda a: (a & 0b1) ^ ((a>>1) & 0b1) , 
        False,
        None, 
        None, 
        None, 
        0b00,
        '^'), 'x'),
    ('Not',([W(0, 'in')],
            [E(0, 'out')],
        lambda a   : not a  , 
        False,
        None, 
        None, 
        None, 
        0b00,
        '~'), 'n'),
    ('High' ,([],
        [E(0)],
        lambda a   : True   , 
        False,
        None, 
        None, 
        None,
        0b00,
        '+'), 'h'),
    ('Low',([],
        [E(0)],
        lambda a    : False  , 
        False,
        None, 
        None, 
        None,
        0b00,
        '-'), 'l'),
    ('Pull-down',([W(0, 'in')],
        [E(0, 'out')],
        lambda a    : (Levels.High if a == Levels.High else Levels.Low)  , 
        True,
        None, 
        None, 
        None,
        0b00,
        '='), 'q'),
)

def UnpackDef(CDef):
    if type(CDef) == tuple:
        return {Key:Value for Key, Value in zip(_DefTuple, CDef)}
    else:
        return CDef

CList = [CName for CName, _, _ in _Definitions]
CDicts = {CName:UnpackDef(CDef) for CName, CDef, _ in _Definitions}
DefaultKeys = {CName:CKey for CName, _, CKey in _Definitions}

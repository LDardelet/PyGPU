import Components

Definitions = {
    'Wire' :Components.Wire,
    'And': ('xy', 'z', '', '',lambda a, b: a and b, None, None, None, '&'),
    'Or' : ('xy', 'z', '', '',lambda a, b: a or b , None, None, None, '|'),
    'Not': ('x' , 'z', '', '',lambda a   : not a  , None, None, None, '~'),
    'True' :(''  , ' ', '', '',lambda     : True   , None, 2   , 2   , '1'),
    'False':(''  , ' ', '', '',lambda     : False  , None, 2   , 2   , '0'),
}

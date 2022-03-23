import Components

class BasicGates:
    Definitions = {
        'AND': ('xy', 'z', '', '',lambda a, b: a & b, None, None, None),
        'OR':  ('xy', 'z', '', '',lambda a, b: a | b, None, None, None),
        'NOT': ('x' , 'z', '', '',lambda a   : ~a   , None, None, None),
    }

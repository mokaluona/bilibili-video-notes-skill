from .mathematics import postfix

RULES = {'mathematics': postfix, 'generic': lambda operator, argument: None}

def register_domain(name, rule):
    """Register a rule returning (node_kind, consumed_characters), a legacy
    node kind for the entire argument, or None for generic handling."""
    if name in RULES:
        raise ValueError('Domain already registered: ' + name)
    RULES[name] = rule

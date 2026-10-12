def postfix(operator, argument):
    # Declare consumption, rather than making the parser know this domain name.
    return ('bar', 1) if operator == '^' and argument.startswith(('c', 'C')) else None

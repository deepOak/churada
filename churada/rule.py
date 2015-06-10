import inspect

class RuleError(Exception):
    pass

class Rule:
    """
    Wrapper for rule-queries
    """
    def __init__(self,key,func):
        self.key = key
        self.func = func
    def query(self,other):
        return self.key in other.__dict__ and self.func(other.__dict__[self.key])

class CompositeRule:
    """
    Allows for arbitrary logical structure composed of rules and logical connectives
     rules is the ordered list of rules
     crule is a lambda function that defines the composite rule 
      ex: lambda x,y: x and y
          lambda x,y,z,a,b,c: (x and y) or (z and a) and (b and not a)
        where x,y,z,a,b,c are rules whose truth values depend on the passed object (other)
      
    """
    def __init__(self,rules,crule):
        self.rules = rules
        self.crule = crule
        if len(rules) != len(inspect.getargspec(crule).args):
            raise RuleError("init error: incorrect number of rules")
    def query(self,other):
        query_results = (rule.query(other) for rule in self.rules)
        return self.crule(*query_results)


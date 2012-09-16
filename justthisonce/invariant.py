# Simple class-based invariants
# From http://people.csail.mit.edu/pgbovine/wiki/doku.php?id=pythonclassinvariants

import types

# This will have weird behavior if you change it while running
CHECK_INVARIANTS = True

def public(func):
  def wrapper(self,*__args,**__kw):
    self._checkInvariant() # check before executing
    res = func(self,*__args,**__kw)
    self._checkInvariant() # check after executing
    return res
  return wrapper

def constructor(func):
  def wrapper(self,*__args,**__kw):
    func(self,*__args,**__kw)
    self._checkInvariant() # check after executing constructor
  return wrapper

def EnforceInvariant(name, bases, attrs):
  if CHECK_INVARIANTS:
    for k in attrs:
      if k == '__init__':
        attrs[k] = constructor(attrs[k])
      # ignore private methods that start with '_' (and of course ignore _checkInvariant itself)
      elif k[0] != '_' and k != '_checkInvariant':
        f = attrs[k]
        if isinstance(f, types.FunctionType):
          attrs[k] = public(f)
  return type(name, bases, attrs)

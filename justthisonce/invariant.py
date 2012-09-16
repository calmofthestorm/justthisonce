"""
Simple class-based invariants. Adapted from:
http://people.csail.mit.edu/pgbovine/wiki/doku.php?id=pythonclassinvariants

Provides a metaclass that will call _checkInvariant before and after every
public method and after construction. Also works for getters and setters.
Does NOT call for methods that start with _, including builtins like len or
setitem, as these may be used internally at times when the invariant needs
to be temporarily violated. You must call _checkInvariant manually in such
cases if you wish to check invariants.
"""

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
        elif isinstance(f, property):
          attrs[k] = property(fset=public(f.fset), fget=public(f.fget), \
                              fdel=public(f.fdel))
  return type(name, bases, attrs)

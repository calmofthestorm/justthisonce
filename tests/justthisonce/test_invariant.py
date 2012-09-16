import itertools
import sys
import unittest

import justthisonce.invariant

class Simple(object):
  """Simple class used to ensure the invariants are being enforced as they
     should be."""
  __metaclass__ = justthisonce.invariant.EnforceInvariant

  def __init__(self, num):
    self._number = num
    self._has_number = True

  def _checkInvariant(self):
    assert self._number % 2 == 0
    assert self._has_number == True

  def __eq__(self, other):
    return self._number == other._number and \
           self._has_number == other._has_number

  @property
  def number(self):
    if self._has_number:
      return self._number

  @number.setter
  def number(self, val):
    if self._has_number:
      self._number = val

  @number.deleter
  def number(self):
    if not self._has_number:
      raise AttributeError("number")
    else:
      self._has_number = False

  def getNum(self):
    if self._has_number:
      return self._number

  def setNum(self, val):
    if self._has_number:
      self._number = val

class test_Invariant(unittest.TestCase):
  def test_invariant(self):
    # Invariants must hold after ctor
    a = Simple(2)
    b = Simple(-2)
    self.assertRaises(AssertionError, Simple, 3)

    # Invariants must hold before public methods and properties, even if
    # they would fix it.
    a._number = 5
    self.assertRaises(AssertionError, a.getNum)
    self.assertRaises(AssertionError, a.setNum, 4)
    with self.assertRaises(AssertionError): a.number
    with self.assertRaises(AssertionError): a.number = 4
    a._number = 0

    # Invariants must hold after public methods and properties.
    with self.assertRaises(AssertionError): a.number = 5
    a._number = 0
    self.assertRaises(AssertionError, a.setNum, 5)
    a._number = 0
    with self.assertRaises(AssertionError): del a.number

    # Invariants need not hold for private methods, even ones that cooperate
    # with public ones.
    with self.assertRaises(AssertionError): a.number
    self.assertFalse(a == b)

    # Normal usage shouldn't violate invariants.
    a = Simple(2)
    a.number = 4
    b.setNum(-8)
    a.getNum()
    b.number
    a.number
    b.getNum()

if __name__ == '__main__':
  unittest.main()


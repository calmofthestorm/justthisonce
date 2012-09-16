import itertools
import sys
import unittest

from justthisonce.interval import Interval

def _union_multi(ivals):
  """Unions all args pairwise left-associative."""
  if len(ivals) == 0:
    return Interval()
  else:
    acc = ivals[0]
    for ival in ivals[1:]:
      acc = acc.union(ival)
    return acc

class test_Interval(unittest.TestCase):
  def test_union_empty(self):
    """Test that empty intervals are well behaved."""
    a = Interval()
    b = Interval()
    c = a.union(b)
    d = b.union(a)
    self.assertEqual(a, b)
    self.assertEqual(b, c)
    self.assertEqual(c, d)

  def test_union_sym_comm(self):
    """Test that union is symmetric and commutative."""

    ivals = [Interval(), Interval.fromAtom(4, 2), Interval.fromAtom(6, 3), \
             Interval.fromAtom(11, 2), Interval.fromAtom(13, 15)]
    # If this were much larger we could use a prefix generator but I prefer
    # simplicity to speed in tests.
    correct = _union_multi(ivals)
    for iv in itertools.permutations(ivals):
      self.assertEqual(correct, _union_multi(iv))

  def test_union_merge_start_zero(self):
    """Tests merges for several coumpound intervals, all start at 0."""
    # Simple case with an extra hole in the original spec.
    a = Interval.fromAtoms([(0, 2), (4, 2), (6, 2)])
    b = Interval.fromAtoms([(2, 2)])
    self.assertEqual(a.union(b), Interval.fromAtom(0, 8))

    # Holes filled partially
    a = Interval.fromAtoms([(0, 2), (4, 2), (8, 2), (20, 3)])
    b = Interval.fromAtoms([(2, 1), (6, 1), (10, 5), (16, 4)])
    a_b = a.union(b)
    self.assertEqual(Interval.fromAtoms([(0, 3), (4, 3), (8, 7), (16, 7)]), a_b)
    a_b_c = a_b.union(Interval.fromAtoms([(3, 1), (7, 1)]))
    self.assertEqual(Interval.fromAtoms([(0, 15), (16, 7)]), a_b_c)
    a_b_c_d = a_b_c.union(Interval.fromAtom(15, 1))
    self.assertEqual(Interval.fromAtom(0, 23), a_b_c_d)
    self.assertEqual(len(a_b_c_d), 23)

  def test_union_merge_start_nonzero(self):
    """Tests merges for several coumpound intervals, all starting after 0
       (regression test against special-case bug)"""
    a = Interval.fromAtoms([(1, 2), (5, 2), (9, 2)])
    b = Interval.fromAtoms([(3, 2), (7, 1)])
    a_b = a.union(b)
    self.assertEqual(a_b, Interval.fromAtoms([(1, 7), (9, 2)]))
    a_b_c = Interval.fromAtom(8, 1).union(a_b)
    self.assertEqual(a_b_c, Interval.fromAtom(1, 10))
    self.assertEqual(len(a_b_c), 10)

  def test_eq_neq(self):
    """Makes sure equality and inequality work, since all other tests depend on
       them. I test many values because Python's default eq/neq behavion can
       be weird and miss edge cases."""
    # The other tests thoroughly test eq == true, so I focus on eq == false and
    # both values of ne.
    a = Interval.fromAtoms([(0, 2), (4, 2), (8, 2)])
    empty = Interval()
    self.assertFalse(a == Interval.fromAtoms([(0, 2)]))
    self.assertTrue(a != Interval.fromAtoms([(0, 2)]))

    self.assertTrue(a == a)
    self.assertFalse(a != a)

    self.assertFalse(a == empty)
    self.assertTrue(a != empty)

    self.assertTrue(empty == Interval())
    self.assertFalse(empty != Interval())

    self.assertTrue(empty == empty)
    self.assertFalse(empty != empty)

    b = Interval.fromAtoms([(0, 2), (4, 2), (6, 2)])
    c = Interval.fromAtoms([(0, 2), (4, 4)])
    self.assertTrue(b == c)
    self.assertFalse(b != c)

    self.assertFalse(b != b)
    self.assertTrue(b == b)
    self.assertFalse(c != c)
    self.assertTrue(c == Interval.fromAtoms([(0, 2), (4, 4)]))

  def test_constructor_equiv(self):
    """Make sure the from* constructors are equivalent. (Default is tested
       with union)."""
    a = Interval.fromAtom(3, 4).union(Interval.fromAtom(12, 10))
    b = Interval.fromAtoms([(3, 4), (12, 10)])
    self.assertEqual(a, b)

    c = Interval.fromAtom(3, 4).union(Interval.fromAtom(7, 10))
    d = Interval.fromAtoms([(7, 10), (3, 4)])
    e = Interval.fromAtom(3, 14)
    self.assertEqual(c, d)
    self.assertEqual(d, e)

    # fromAtoms must tolerate 0-length intervals.
    f = Interval.fromAtoms([(0, 2), (2, 0), (2, 2)])
    self.assertEqual(f, Interval.fromAtom(0, 4))

    # and must not tolerate overlap.
    with self.assertRaises(AssertionError):
      Interval.fromAtoms([(0, 5), (4, 5)])

  def test_len(self):
    """Specifically test len. This is also being tested in the object invariant
       throughout the entire test suite so we just do a quick one here."""
    a = Interval.fromAtom(3, 3)
    b = Interval.fromAtom(9, 5)
    self.assertEqual(len(a) + len(b), len(a.union(b)))
    self.assertEqual(len(a), 3)
    self.assertEqual(len(b), 5)
    self.assertEqual(len(Interval()), 0)

  def test_union_overlap(self):
    """It is part of the design spec that intervals to union must be disjoint,
       since otherwise would likely indicate an error in the main program."""
    # Off by one
    with self.assertRaises(AssertionError):
      Interval.fromAtom(0, 5).union(Interval.fromAtom(4, 5))
    a = Interval.fromAtom(0, 5).union(Interval.fromAtom(5, 5))
    self.assertEqual(a, Interval.fromAtom(0, 10))

    # Containment
    with self.assertRaises(AssertionError):
      Interval.fromAtom(0, 5).union(Interval.fromAtom(2, 1))
    with self.assertRaises(AssertionError):
      Interval.fromAtom(2, 1).union(Interval.fromAtom(0, 5))

    # Overlap by 1 (regression test)
    with self.assertRaises(AssertionError):
      Interval.fromAtom(0, 5).union(Interval.fromAtom(4, 1))
    
    # Multiple intervals
    b = Interval.fromAtoms([(2, 3), (10, 3), (20, 10000)])
    with self.assertRaises(AssertionError):
      Interval.fromAtom(0, 5).union(b)
    with self.assertRaises(AssertionError):
      Interval.fromAtom(2, 19).union(b)
    with self.assertRaises(AssertionError):
      Interval.fromAtom(900, 2).union(b)

    # With self
    with self.assertRaises(AssertionError):
      a.union(a)
    with self.assertRaises(AssertionError):
      b.union(b)

if __name__ == '__main__':
  unittest.main()


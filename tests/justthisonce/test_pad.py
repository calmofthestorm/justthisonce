import itertools
import sys
import unittest

from justthisonce.pad import *

class test_File(unittest.TestCase):
  pass

class test_Allocation(unittest.TestCase):
  def setUp(self):
    self._next_uuid = 0

  def _uuid(self):
    self._next_uuid += 1
    return self._next_uuid - 1

  def _make_test_allocation(self, filesize, istart, ilen, padfile=None):
    if padfile is None:
      padfile = File("myfile%i" % self._uuid(), filesize, "current")
    a = Allocation(padfile, istart, ilen)
    return a, list(a.iterFiles()), padfile

  def _assert_equal_no_order(self, a, b):
    def key((ival, padfile)):
      return (padfile.filename, ival.min())
    self.assertEqual(sorted(a.iterFiles(), key=key),
                     sorted(b.iterFiles(), key=key))

  @staticmethod
  def _symmetric_union(a, b):
    return a.union(b), b.union(a)

  def test_ctor(self):
    """Tests the two forms of the constructor."""
    a = Allocation()
    self.assertEqual(len(a), 0)
    files = list(a.iterFiles())
    self.assertEqual(len(list(a.iterFiles())), 0)

    # Test a few combinations of file size and interval that should work.
    for (filesize, istart, ilen) in \
        [(10, 0, 10), (2000, 50, 100), (100, 0, 5), (100, 90, 10)]:
      a, files, padfile = self._make_test_allocation(filesize, istart, ilen)
      self.assertEqual(len(a), ilen)
      self.assertEqual(files, [(Interval.fromAtom(istart, ilen), padfile)])

    # 0-length intervals violate the invariant, as do those that exceed
    # file bounds.
    for (filesize, istart, ilen) in \
        [(10, 5, 0), (10, 5, 15), (10, 12, 5), (10, -5, 5), (10, 5, -2)]:
      self.assertRaises(AssertionError,
                        self._make_test_allocation, filesize, istart, ilen)

    # Enforce ctor form.
    padfile = File("myfile", 50, "current")
    for args in [(padfile, 40, None), (padfile, None, 5), (None, 40, 5), \
                 (padfile, None, None), (None, 40, None), (None, None, 5)]:
      self.assertRaises(AssertionError, Allocation, *args)

  def test_unionUpdate(self):
    """Test allocation unionUpdate."""
    a, a_files, a_padfile = self._make_test_allocation(30, 10, 20)
    b, b_files, b_padfile = self._make_test_allocation(250, 15, 35)
    padfile = File("myfile%i" % self._uuid(), 10, "current")
    a.unionUpdate(Allocation(padfile, 5, 5))
    b.unionUpdate(Allocation(padfile, 0, 4))
    a_b = Allocation()
    a_b.unionUpdate(a)
    a_b.unionUpdate(b)

    b_a = Allocation()
    b_a.unionUpdate(b)
    b_a.unionUpdate(a)
    self._assert_equal_no_order(a_b, b_a)
    self.assertNotEqual(a_b, b_a)
    self.assertNotEqual(a, b)
    self.assertEqual(len(b_a), 64)
    self.assertEqual(len(a_b), 64)

  def test_iterFiles(self):
    """Tests allocation's iterFiles"""
    a, a_files, a_padfile = self._make_test_allocation(50, 20, 10)
    b = Allocation()
    c, c_files, c_padfile = self._make_test_allocation(10, 2, 1)
    a_atom = (Interval.fromAtom(20, 10), a_padfile)
    c_atom = (Interval.fromAtom(2, 1), c_padfile)

    self.assertEqual(list(b.iterFiles()), [])
    self.assertEqual(list(a.iterFiles()), [a_atom])
    self.assertEqual(list(c.iterFiles()), [c_atom])
    a, c = self._symmetric_union(a, c)
    self.assertEqual(list(a.iterFiles()), [a_atom, c_atom])
    self.assertEqual(list(c.iterFiles()), [c_atom, a_atom])

  def test_union(self):
    """Test allocation union."""
    # Two empty
    self.assertEqual(Allocation().union(Allocation()), Allocation())

    # One empty
    a, files, padfile = self._make_test_allocation(50, 10, 20)
    b = Allocation()
    c = Allocation()
    a_b = a.union(b)
    b_a = b.union(a)
    self.assertEqual(a_b, b_a)
    self.assertEqual(a_b, a)
    self.assertEqual(len(a_b), 20)

    # Both have one file (different)
    a, a_files, a_padfile = self._make_test_allocation(30, 10, 20)
    b, b_files, b_padfile = self._make_test_allocation(250, 15, 35)
    a_b = a.union(b)
    b_a = b.union(a)
    self._assert_equal_no_order(a_b, b_a)
    self.assertNotEqual(a, b)
    self.assertNotEqual(a_b, b_a)
    self.assertEqual(len(a_b), 55)
    self.assertEqual(len(b_a), 55)

    # Both have the same file
    a, a_files, padfile = self._make_test_allocation(250, 10, 20)
    b, b_files, padfile = self._make_test_allocation(250, 30, 50,
                                                       padfile=padfile)
    self.assertNotEqual(a, b)
    a, b = self._symmetric_union(a, b)
    self._assert_equal_no_order(a, b)
    self.assertEqual(len(a), 70)
    self.assertEqual(len(b), 70)

    # Each has two files, one is common.
    a, a_files, a_padfile = self._make_test_allocation(30, 10, 20)
    b, b_files, b_padfile = self._make_test_allocation(250, 15, 35)
    padfile = File("myfile%i" % self._uuid(), 10, "current")
    a = a.union(Allocation(padfile, 5, 5))
    b = b.union(Allocation(padfile, 0, 4))
    self.assertNotEqual(a, b)
    a, b = self._symmetric_union(a, b)
    self._assert_equal_no_order(a, b)
    self.assertNotEqual(a, b)
    self.assertEqual(len(b), 64)
    self.assertEqual(len(a), 64)

if __name__ == '__main__':
  unittest.main()

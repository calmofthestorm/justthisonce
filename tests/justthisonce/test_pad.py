import itertools
import mock
import shutil
import sys
import tempfile
import unittest

from cStringIO import StringIO
import cPickle as pickle

from justthisonce.pad import *

def sideEffect(**kw):
  """Returns a side effect function for mocks. Will return K:V for given. As a
     special case, will raise exception values."""
  def effector(k):
    v = kw[k]
    if isinstance(v, Exception):
      raise v
    else:
      return v
  return effector

class test_File(unittest.TestCase):
  def _process_alloc_to_ival(self, alloc, padfile, length):
    files = list(alloc.iterFiles())
    self.assertEqual(len(files), 1)
    (ival, pf), = files
    self.assertEqual(length, len(ival))
    self.assertEqual(padfile, pf)
    return ival

  def test_lifecycle(self):
    """Tests a lifecycle use of the file class."""
    a = File("myfile", 50, "current")
    self.assertEqual(a.free, 50)
    self.assertEqual(a.path, ("current", "myfile"))
    alloc = self._process_alloc_to_ival(a.getAllocation(35), a, 35)
    
    # Alloc has not been committed yet so the space is still free
    self.assertEqual(a.free, 50)

    # This allocation will overlap, so not both may be committed. This is
    # enforced in the Pad, but here we should get an invariant warning.
    alloc2 = self._process_alloc_to_ival(a.getAllocation(5), a, 5)
    a.commitAllocation(alloc)
    self.assertRaises(AssertionError, a.commitAllocation, alloc2)

    # Can't commit twice!
    self.assertRaises(AssertionError, a.commitAllocation, alloc)

    # But it should work if we get a new one
    alloc2 = self._process_alloc_to_ival(a.getAllocation(5), a, 5)
    self.assertEqual(len(alloc2), 5)
    a.commitAllocation(alloc2)
    self.assertEqual(a.free, 10)
    self.assertEqual(a.used, 40)

    # Can't ask for more than there is!
    self.assertRaises(OutOfPad, a.getAllocation, 11)

    # But this is ok because they can't all commit.
    a.getAllocation(9)
    a.getAllocation(10)

    # Let's fill it up.
    alloc = self._process_alloc_to_ival(a.getAllocation(9), a, 9)
    a.commitAllocation(alloc)
    self.assertEqual(a.free, 1)
    self.assertEqual(a.used, 49)

    alloc = self._process_alloc_to_ival(a.getAllocation(1), a, 1)
    a.commitAllocation(alloc)
    self.assertEqual(a.free, 0)
    self.assertEqual(a.used, 50)
    self.assertRaises(OutOfPad, a.getAllocation, 11)

  def test_consumeEntireFile(self):
    """Tests that consumeEntireFile works."""
    fi = File("myfile", 0, "current")
    fi.consumeEntireFile()
    self.assertEqual(fi.free, 0)
    
    fi = File("myfile", 50, "incoming")
    fi.commitAllocation(self._process_alloc_to_ival(fi.getAllocation(25),
                                                    fi, 25))
    self.assertEqual(fi.free, 25)
    fi.consumeEntireFile()
    self.assertEqual(fi.free, 0)

    fi = File("myfile", 5, "spent")
    fi.commitAllocation(self._process_alloc_to_ival(fi.getAllocation(5),
                                                    fi, 5))
    self.assertEqual(fi.free, 0)

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
        [(10, 5, 15), (10, 12, 5), (10, -5, 5), (10, 5, -2)]:
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

class test_Filesystem(unittest.TestCase):
  def test_sanity(self):
    """Simple sanity checks."""
    # We don't support root because it makes things harder and is not a useful
    # feature.
    self.assertRaises(AssertionError, Filesystem, "/")

  def setUp(self):
    """Creates an empty filesystem."""
    self.fsdir = tempfile.mkdtemp()
    self.fsroot = os.path.split(self.fsdir)
    self.fs = Filesystem(self.fsdir)

  def _populate(self):
    """Populates the test fs with some files."""
    for subdir in "current", "incoming", "spent":
      self.fs.mkdir(subdir)
      self.fs.open((subdir, "%spad" % subdir[0]), 'w')

  def tearDown(self):
    """Cleans up the generated files."""
    assert self.fsdir.startswith(tempfile.gettempdir())
    shutil.rmtree(self.fsdir)

  def test_relpath(self):
    """Tests relpath"""
    # We SHOULD be able to see the root of the dir
    self.assertEqual(self.fsdir, self.fs._relpath(self.fsroot))
    self.assertEqual(self.fsdir, self.fs._relpath(self.fsdir))
    self.assertEqual(self.fsdir, self.fs._relpath((self.fsdir,)))
    self.assertEqual(self.fsdir, self.fs._relpath("."))
    self.assertEqual(self.fsdir, self.fs._relpath((".",)))

    # We SHOULD be able to see files under the dir
    self.assertEqual(self.fsdir + "/a/b/c", self.fs._relpath(("a", "b", "c")))
    self.assertEqual(self.fsdir + "/a/b/c", self.fs._relpath("a/b/c"))
    self.assertEqual(self.fsdir + "/a/b/c", self.fs._relpath(("a/b", "c")))

    # We should NOT be able to do evil things.
    self.assertRaises(AssertionError, self.fs._relpath, ("/"))
    self.assertRaises(AssertionError, self.fs._relpath, (("../etc", "shadow")))
    self.assertRaises(AssertionError, self.fs._relpath, (("../etc/shadow")))
    self.assertRaises(AssertionError, self.fs._relpath, (("../../etc/shadow")))
    self.assertRaises(AssertionError, self.fs._relpath, \
                      (("..", "..", "..", "etc", "shadow")))

    # Even if we ask nicely.
    self.assertRaises(AssertionError, self.fs._relpath, (("/", "etc", "shadow")))

    # Or strangely
    self.assertRaises(AssertionError, self.fs._relpath, ((u"/etc/shadow")))
    self.assertRaises(AssertionError, self.fs._relpath, (("/etc/shadow",)))
    self.assertRaises(AssertionError, self.fs._relpath, (("/", "etc", "shadow")))
    self.assertRaises(AssertionError, self.fs._relpath, \
                      (("..", u"..", "..", u"etc", "shadow")))

  def test_mkdir(self):
    """Tests mkdir"""
    self.fs.mkdir("current")
    self.fs.mkdir("current/more")
    self.assertRaises(OSError, self.fs.mkdir, "current/more/")
    self.assertRaises(OSError, self.fs.mkdir, "current/more/is/less")
    self.assertRaises(AssertionError, self.fs.mkdir, "/evil")
    self.assertRaises(AssertionError, self.fs.mkdir, "../evil")

    self.fs.setReadonly()
    self.assertRaises(AssertionError, self.fs.mkdir, "currente")
    self.assertRaises(AssertionError, self.fs.mkdir, ("currente", "moree"))

  def test_exists(self):
    """Tests exists"""
    self.assertFalse(self.fs.exists("current"))
    self.assertFalse(self.fs.exists(("current", "padfile")))
    self._populate()
    self.assertFalse(self.fs.exists(("current", "padfile")))
    self.assertTrue(self.fs.exists(("current", "cpad")))
    self.assertTrue(self.fs.exists("spent"))
    self.assertFalse(self.fs.exists(("current", "spad")))
    self.assertTrue(self.fs.exists(("spent", "spad")))

    self.fs.setReadonly()
    self.assertFalse(self.fs.exists(("current", "spad")))
    self.assertTrue(self.fs.exists(("spent", "spad")))

  def test_stat(self):
    """Tests stat"""
    self._populate()
    for testpath in [("current",), ("current", "cpad"), (".",)]:
      self.assertEqual(os.stat(os.path.join(self.fsdir, *testpath)), \
                       self.fs.stat(testpath))

    self.fs.setReadonly()
    self.fs.stat(("current", "cpad"))

  def test_listdir(self):
    """Tests listdir"""
    self.assertEqual(self.fs.listdir("."), [])
    self._populate()
    self.assertEqual(set(self.fs.listdir(".")), \
                     set(["current", "spent", "incoming"]))
    for subdir in "current", "incoming", "spent":
      self.assertEqual(self.fs.listdir(subdir), ["%spad" % subdir[0]])
      self.assertRaises(OSError, self.fs.listdir, (subdir, "%spad" % subdir[0]))
      self.assertRaises(OSError, self.fs.listdir, (subdir, "%spad_dne" % subdir[0]))


    self.fs.setReadonly()
    self.assertEqual(set(self.fs.listdir(".")), \
                     set(["current", "spent", "incoming"]))

  def test_rename(self):
    """Tests rename"""
    self.assertRaises(OSError, self.fs.rename, "current", "currant")
    self._populate()
    self.fs.rename("current", "currant")
    self.fs.rename("currant", "current")
    self.fs.rename(("spent", "spad"), ("current", "cpad"))
    self.assertRaises(OSError, self.fs.rename, ("spent", "spad"),
                      ("current", "cpad"))
    self.assertFalse(self.fs.exists(("spent", "cpad")))
    self.assertFalse(self.fs.exists(("spent", "spad")))
    self.assertTrue(self.fs.exists(("current", "cpad")))

    self.fs.setReadonly()
    self.assertRaises(AssertionError, self.fs.rename, ("incoming", "ipad"),
                      ("current", "ipad"))

  def test_open(self):
    """Tests open"""
    self._populate()
    self.assertEqual(self.fs.open(("current", "cpad")).read(), "")
    self.assertRaises(IOError, self.fs.open, ("current", "foo"))
    self.fs.open(("current", "foo"), 'w').write("Hello")
    self.assertEqual(self.fs.open(("current", "foo")).read(), "Hello")

    self.fs.setReadonly()
    self.assertRaises(AssertionError, self.fs.open, ("current", "food"), 'w')
    self.assertEqual(self.fs.open(("current", "foo")).read(), "Hello")

class test_Pad(unittest.TestCase):
  def setUp(self):
    self.fs = mock.create_autospec(Filesystem)

  def test_createPad_normal(self):
    """Tests create pad when nothing goes wrong."""
    # verify we create the structure when everything works
    fs = self.fs("/tmp")
    def verify_created(fs):
      fs.open.side_effect = metadata, version = [StringIO(), StringIO()]

      Pad.createPad(fs)
      fs.open.assert_has_calls([mock.call("metadata.pck", 'w'),
                                mock.call("VERSION", 'w')])

      self.assertEqual(pickle.loads(metadata.getvalue()).__dict__,
                       Metadata().__dict__)
      self.assertEqual(version.getvalue(), "%s\n%s" % (COMPAT, VERSION))
      fs.mkdir.assert_any_call("current")
      fs.mkdir.assert_any_call("spent")
      fs.mkdir.assert_any_call("incoming")

    # Should work if the dir is empty OR does not exist. Must make if does not
    # exist, must check empty if does.
    fs.exists.return_value = False
    fs.listdir.side_effect = OSError
    verify_created(fs)
    fs.mkdir.assert_any_call(".")

    fs.reset_mock()
    fs.exists.return_value = True
    fs.listdir.side_effect = None
    fs.listdir.return_value = []
    verify_created(fs)
    fs.listdir.assert_called_with(".")

  def test_createPad_error(self):
    """Tests some failure modes of createPad."""

    # Dir exists but has a file/subdir
    fs = self.fs("/tmp")
    fs.listdir.return_value = ["foo"]
    fs.exists.side_effect = lambda x: x in (".", "foo")
    self.assertRaises(InvalidPad, Pad.createPad, fs)

  class InitBypass(Pad):
    """Class used to bypass init so it can be tested componentwise. We could
       go to a construct / initialize workflow but this seems more Pythonic."""
    def __init__(self):
      pass

  def test__loadMetadata(self):
    """Tests _loadMetadata (init helper)"""

    # Test missing metadata
    pad = self.InitBypass()
    pad._fs = self.fs("/tmp")
    pad._fs.open.side_effect = \
        sideEffect(VERSION=StringIO("%s\n%s" % (COMPAT, VERSION)), \
                   **{"metadata.pck":IOError()})
    self.assertRaisesRegexp(InvalidPad, "Metadata missing or corrupt",
                            pad._loadMetadata)

    # Test missing version
    pad = self.InitBypass()
    pad._fs = self.fs("/tmp")
    pad._fs.open.side_effect = \
        sideEffect(**{"VERSION":IOError(),
                      "metadata.pck":StringIO(cPickle.dumps(Metadata()))})
    self.assertRaisesRegexp(InvalidPad, "Version missing or corrupt",
                            pad._loadMetadata)

    # Test corrupt metadata
    pad = self.InitBypass()
    pad._fs = self.fs("/tmp")
    pad._fs.open.side_effect = \
        sideEffect(**{"VERSION":StringIO("%s\n%s" % (COMPAT, VERSION)),
                      "metadata.pck":StringIO("a" + cPickle.dumps(Metadata()))})
    self.assertRaisesRegexp(InvalidPad, "Metadata missing or corrupt",
                            pad._loadMetadata)

    # Test corrupt version
    pad = self.InitBypass()
    pad._fs = self.fs("/tmp")
    pad._fs.open.side_effect = lambda fn: files[fn]
    pad._fs.open.side_effect = \
        sideEffect(**{"VERSION":StringIO("Potato\n13"),
                      "metadata.pck":StringIO(cPickle.dumps(Metadata()))})
    self.assertRaisesRegexp(InvalidPad, "Version missing or corrupt",
                            pad._loadMetadata)

    # Test newer and older version, as well as current one.
    for version in range(VERSION - 1, VERSION + 2):
      for compat in range(COMPAT - 1, COMPAT + 1):
        # Test everything works
        pad = self.InitBypass()
        pad._fs = self.fs("/tmp")
        files = {"metadata.pck":StringIO(cPickle.dumps(Metadata())), \
                 "VERSION":StringIO("%s\n%s" % (compat, version))}
        pad._fs.open.side_effect = sideEffect(**files)
        pad._loadMetadata()

    # Test incompat version
    pad = self.InitBypass()
    pad._fs = self.fs("/tmp")
    files = {"metadata.pck":StringIO(cPickle.dumps(Metadata())), \
             "VERSION":StringIO("%s\n%s" % (COMPAT + 1, VERSION + 1))}
    pad._fs.open.side_effect = lambda fn: files[fn]
    self.assertRaisesRegexp(InvalidPad, "Pad is protocol.*but I only understand.*", \
                            pad._loadMetadata)

  def test__verifyDirStructure(self):
    """Tests _verifyDirStructure (init helper)"""
    # Test all good
    pad = self.InitBypass()
    pad._fs = self.fs("/tmp")
    pad._fs.exists.side_effect = lambda fn: fn in ("incoming", "spent", "current")

    # Empty dir
    pad._fs.listdir.return_value = []
    pad._verifyDirStructure()

    # Now with some conflicting files
    pad._fs.listdir.side_effect = sideEffect(incoming="ab", spent="bc",
                                             current="d")
    self.assertRaisesRegexp(InvalidPad, "Duplicate pad filenames.*", \
                            pad._verifyDirStructure)

    # Now with some files that do not conflict
    pad._fs.listdir.side_effect = sideEffect(incoming="abgde", spent="yz",
                                             current="t")
    pad._verifyDirStructure()
    pad._fs.listdir.side_effect = sideEffect(incoming="a", spent="b", current="")
    pad._verifyDirStructure()

    # Now a directiory is missing
    pad._fs.exists.side_effect = lambda fn: fn in ("incoming", "spent")
    self.assertRaisesRegexp(InvalidPad, "Directory structure bad", \
                            pad._verifyDirStructure)
    pad._fs.exists.side_effect = lambda fn: fn in ("incoming", "current")
    self.assertRaisesRegexp(InvalidPad, "Directory structure bad", \
                            pad._verifyDirStructure)

if __name__ == '__main__':
  unittest.main()



"""
The pad module is responsible for curating the store of pad material and
tracking use. The pad directory has three subdirs: incoming, current, and
spent.
"""

import cPickle
import os
import collections

from justthisonce.interval import Interval
from justthisonce import invariant

COMPAT = 0
VERSION = 0

class Error(Exception):
  """Base error for the pad module."""

class InvalidPad(Error):
  """The on-disk pad structure has broken invariants, is corrupt, etc, and
     there is no obvious way to repair it."""

class PadDirty(Error):
  """The on-disk pad is in an odd state but we can probably fix it safely."""

class OutOfPad(Error):
  """There is not enough pad remaining to allocate the requested range."""

class AllocationOutstanding(Error):
  """Cannot allocate another while one is outstanding."""

class File(object):
  """Holds data on what parts of a file have already been used."""
  __metaclass__ = invariant.EnforceInvariant

  def __init__(self, filename, size, subdir):
    # Total size of the file
    self.size = size

    # Number of bytes in the file that have been used already.
    self.used = 0

    # Relative name of the file.
    self.filename = filename

    # Regions of the file in use.
    self._extents = Interval()

    # Subdir the file is currently in.
    self.subdir = subdir

  def _checkInvariant(self):
    assert self.size >= self.used
    assert len(self._extents) == self.used

  @property
  def free(self):
    return self.size - self.used

  @property
  def path(self):
    """Returns the path of the padfile relative to the paddir."""
    return (self.subdir, self.filename)

  def getAllocation(self, requested):
    """Requests an allocation from the file of the given size. Raises OutOfPad
       if the file is out of space."""
    if requested > self.free:
      raise OutOfPad("File %s has %i bytes but you requested %i." % \
                     (self.filename, self.free, requested))

    alloc = Allocation()
    for (start, length) in self._extents.iterExterior(self.size):
      seg = Allocation(self, start, min(requested - len(alloc), length))
      alloc.unionUpdate(seg)
      if len(alloc) >= requested:
        assert len(alloc) == requested
        break

    assert len(alloc) == requested
    return alloc

  def commitAllocation(self, ival):
    """Mark the specified interval as used. Error if overlaps with currently
       used area."""
    self._extents = self._extents.union(ival)
    self.used += len(ival)

  def consumeEntireFile(self):
    """Mark the entire file as consumed. Used to prevent its use for encryption
       while keeping it around for decryption."""
    self.used = self.size
    self._extents = Interval.fromAtom(0, self.size)

class Allocation(object):
  """Holds an allocation on te pad, which may contain multiple chunks in
     multiple files. They may be constructed with union-like updates."""
  __metaclass__ = invariant.EnforceInvariant

  def __init__(self, padfile=None, start=None, length=None):
    """With no arguments, creates an empty allocation. With three, creates an
       allocation with a single interval (which must not be empty.)"""

    # Mapping from filename to (interval, padfile)
    self._alloc = collections.OrderedDict()
    self._size = 0

    if padfile is None or start is None or length is None:
      assert padfile is None and start is None and length is None
    else:
      self._alloc[padfile.filename] = (Interval.fromAtom(start, length), \
                                       padfile)
      self._size = length

  def _checkInvariant(self):
    # Size of an allocation must be the sum of the lengths of its' intervals.
    assert self._size == sum((len(ival) \
                              for (ival, _) in self._alloc.itervalues()))

    # Intervals must not exceed size of file.
    assert all((len(ival) == 0 or (ival.max() < padfile.size and ival.min()>=0)\
                for (ival, padfile) in self._alloc.itervalues()))

    # A file may not appear more than once
    files = list(self._alloc.iterkeys())
    assert len(files) == len(set(files))

  def __len__(self):
    return self._size

  def unionUpdate(self, other):
    rval = self.union(other)
    self._alloc = rval._alloc
    self._size = rval._size

  def union(self, other):
    """Combines two allocations, merging adjacent intervals in the same file.
       The result will have my files first, merged with the other's as
       appropriate, followed by the files just in the other."""
    merged = collections.OrderedDict()
    for (filename, (ival, padfile)) in self._alloc.iteritems():
      if filename in other._alloc:
        other_ival, other_padfile = other._alloc[filename]
        assert other_padfile is padfile
        merged[filename] = (ival.union(other_ival), padfile)
      else:
        merged[filename] = (ival, padfile)

    # Add in any files just in the other.
    for (filename, (ival, padfile)) in other._alloc.iteritems():
      merged.setdefault(filename, (ival, padfile))

    rval = Allocation()
    rval._size = self._size + other._size
    rval._alloc = merged
    return rval

  def iterFiles(self):
    """Returns an iterator of (interval, file)."""
    return self._alloc.itervalues()
  
  def __eq__(self, other):
    # Order matters!
    return self._size == other._size and self._alloc == other._alloc

  def __ne__(self, other):
    return not self.__eq__(other)

class Metadata(object):
  """Represents all metadata of the pad that is saved to disk."""

  def __init__(self):
    self.current = []
    self.compatability = None
    self.version = None

class Filesystem(object):
  """Shim class to abstract interactions with the filesystem. This makes it
     easier to test Pad and also improves flexibility for changes to backend
     and reduces points of failure for directory traversal attacks
     (a malicious message could trivially write any file on the system to the
     output file without this by claiming to be encrypted with that file and
     sending a known/zeroed message). All paths are given as component tuples
     except that of root in the constructor."""

  def __init__(self, path):
    """Assumes control of the directory at path. Path may not be root."""
    assert path != "/"
    self.root = path
    self._readonly = False

  def _relpath(self, path):
    """Returns the given path relative to the start. Raises assertion if
       is not a subdir of the path given in the ctor."""
    if isinstance(path, basestring):
      path = path,
    relpath = os.path.abspath(os.path.join(self.root, *path))
    assert os.path.commonprefix((relpath, self.root)) == self.root
    return os.path.join(self.root, relpath)

  def setReadonly(self):
    """Enters readonly mode. No further changes to the managed directory
       will occur."""
    self._readonly = True

  def mkdir(self, path):
    """Wraps os.mkdir relative to the root."""
    assert not self._readonly
    os.mkdir(self._relpath(path))

  def exists(self, path):
    """Wraps os.path.exists relative to the root."""
    return os.path.exists(self._relpath(path))

  def stat(self, path):
    """Wraps os.stat relative to the root."""
    return os.stat(self._relpath(path))

  def listdir(self, path):
    """Wraps os.listdir relative to the root."""
    return os.listdir(self._relpath(path))

  def rename(self, old, new):
    """Wraps os.rename relative to the root."""
    assert not self._readonly
    return os.rename(self._relpath(old), self._relpath(new))

  def open(self, path, mode='r', buffering=-1):
    """Wraps open relative to the root."""
    assert not self._readonly or set("rbU").issuperset(mode)
    return open(self._relpath(path), mode, buffering)

class Pad(object):
  """Represents an on-disk pad dir."""
  __metaclass__ = invariant.EnforceInvariant

  @classmethod
  def createPad(cls, fs):
    """Creates a new pad on the provided fs. Will not clobber an
       exinting non-emptf directory."""
    if fs.exists("."):
      if fs.listdir("."):
        raise InvalidPad("Directory exists and is not empty.")
    else:
      fs.mkdir(".")

    for subdir in "incoming", "current", "spent":
      fs.mkdir(subdir)
    cPickle.dump(Metadata(), fs.open("metadata.pck", 'w'), -1)
    fs.open("VERSION", 'w').write("%s\n%s" % (COMPAT, VERSION))

  def _loadMetadata(self):
    """Helper for init. Loads the metadata from the filesystem. Raises
       InvalidPad if the metadata is bad or from an unsupperted version."""
    # Try to load the metadata
    try:
      self.metadata = cPickle.load(self._fs.open("metadata.pck"))
    except:
      raise InvalidPad("Metadata missing or corrupt")

    # Check the version and compatability
    try:
      self.metadata.compatability, self.metadata.version = \
          map(int, self._fs.open("VERSION").read().split("\n"))
    except:
      raise InvalidPad("Version missing or corrupt")

    # Make sure the pad is compatable
    if self.metadata.compatability > COMPAT:
      raise InvalidPad("Pad is protocol %i but I only understand up to %i" % \
                       (self.metadata.compatability, COMPAT))

  def _verifyDirStructure(self):
    """Helper for init. Verifies the structure in the paddir is valid."""
    fn = []
    for subdir in "incoming", "current", "spent":
      if not self._fs.exists(subdir):
        raise InvalidPad("Directory structure bad")
      fn.extend(self._fs.listdir(subdir))
    if len(fn) != len(set(fn)):
      raise InvalidPad("Duplicate pad filenames detected. " \
                       "Filenames must be unique.")

  def _findMissingPads(self):
    """Helper for init. Looks for missing pads and sets readonly on the
       fs if any are found."""
    for i in reversed(range(len(self.metadata.current))):
      entry = self.metadata.current[i]
      assert entry.subdir == "current"
      if not self._fs.exists((entry.subdir, entry.filename)):
        if entry.used in (0, entry.size):
          # Unused or consumed pad found in current. This is probably ok.
          self._fs.set_readonly()
          del self.metadata.current[i]
        elif self._fs.exists(("incoming", entry.filename)):
          # Padfile found in incoming but expected in current.
          self._fs.set_readonly()
          entry.subdir = "incoming"
        elif self._fs.exists(("spent", entry.filename)):
          # Pad found in spent but was not marked as used up in metadata.
          self._fs.set_readonly()
          entry.subdir = "spent"
          entry.consumeEntireFile()
        else:
          # Missing non-unused padfile.
          self._fs.set_readonly()
          del self.metadata.current[i]

  def _verifyPadfileSize():
    """Helper for init. Verifies all pad sizes."""
    for i in reversed(range(len(self.metadata.current))):
      entry = self.metadata.current[i]
      actual = self._fs.stat(("current", entry.filename))
      if entry.size != actual:
        # Current pad file changed size
        self._fs.set_readonly()

        # Can't trust it anymore. Mark it as spent but don't delete so can at
        # least try to decrypt.
        entry.consumeEntireFile()

  def __init__(self, fs, fsck=False):
    """Opens a pad. If create is True, will initialize
       the pad if it does not exist."""
    self._fs = fs
    self._uncomitted = 0
    if not self._fs.exists("."):
      raise InvalidPad("No such file or directory.")
    
    # Try to load the metadata
    self._loadMetadata()

    # Verify directory structure and check for duplicate filenames.
    self._verifyDirStructure()

    # Check for pads that are in metadata but not on-disk. If they
    # have any used space, their absence is an error but if not, they may
    # be stragglers left over from an interrupted "claiming" of a new
    # pad file, and we can savely remove their metadata.
    self._findMissingPads()

    # Verify the size of all pads that are in use
    self._verifyPadfileSize() 

    # Flush metadata
    self.flush()

  def _checkInvariant(self):
    assert self._uncomitted in (0, 1)

  def flush(self):
    """Flush the pad's current state to disk but do not close it. This will
       not discard uncommitted transactions, but they will not be saved to
       disk. This is intentional -- If we crash before a txn is explicitly
       committed, it should be rolled back."""
    # Save old as a backup in case the dump fails. Routines that move the
    # actual files around should be able to tolerate reverting to these if
    # flush/close raises an exception.
    #TODO write recovery code and inttest it
    self._fs.rename("metadata.pck", "metadata.bkp")
    self._fs.rename("VERSION", "metadata.bkp")
    cPickle.dump(self.metadata, open("metadata.pck", 'w'), -1)
    self._fs.open("VERSION", 'w').write("%s\n%s" % (COMPAT, VERSION))

  def getAllocation(self, requested):
    """Requests the pad to allocate requested bytes of pad. Returns an
       Allocation or raises OutOfPad if there is no pad left. This should
       not modify the state of the pad in any way except to mark that there
       is an uncommitted allocation pending. This is done to force serialization
       of pad claiming to prevent accidental reuse of the same key material."""
    # Look through the files we are already using first.
    current_free = sum((pad.free for pad in self.metadata.current))

    if current_free < requested:
      # We need more pad. Look through incoming to see if we can service the
      # request, beginning with the smallest files.
      can_get = 0
      new_pads = [(fn, self._fs.stat(("incoming", fn)).st_size) \
                  for fn in os.listdir("incoming")]
      new_pads.sort(lambda (pad, size): size)
      last_need = -1
      for last_need, (pad, size) in enumerate(new_pads):
        can_get += size
        if can_get + current_free >= requested:
          break
      else:
        raise OutOfPad("Can't allocate %i bytes; %i bytes available" \
                       % (requested, can_get))


    new_files = [File(pad, size, "incoming") \
                 for (pad, size) in new_pads[:last_need + 1]]

    # There is now enough space to actually allocate in current.
    needed = requested
    allocation = Allocation()
    for pad in self.metadata.current + new_files:
      newb = pad.getAllocation(min(needed - len(allocation), pad.free))
      allocation.unionUpdate(newb)

    assert len(allocation) == requested
    self._uncomitted += 1
    return allocation

  def discardUncommitted(self):
    """Releases any outstanding allocations."""
    self._uncomitted = 0
  
  def commitAllocation(self, alloc):
    """Commits the use of an allocation, and writes the updated metadata
       and any file moves to disk."""
    assert self._uncomitted == 1
    self.discardUncommitted()

    # Move any files in incoming
    for (ival, padfile) in alloc.iterFiles():
      if padfile not in self.metadata.current:
        assert padfile.subdir == "incoming"
        os.rename(padfile.path, ("current", padfile.filename))
        padfile.subdir = "current"

      # Mark used extents as used in file, and move to spent if necessary
      padfile.markIntervalAsUsed(ival)
      if padfile.free == 0:
        os.rename(padfile.path, ("spent", padfile.filename))
      
    # Write out the metadata
    self.flush()

  @property
  def uncommitted(self):
    return self._uncomitted

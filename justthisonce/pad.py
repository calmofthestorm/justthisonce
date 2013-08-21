"""
The pad module is responsible for curating the store of pad material and
tracking use. The pad directory has three subdirs: incoming, current, and
spent.
"""

import cPickle
import os
import collections
import sqlite3
import uuid as uuidlib

from justthisonce.interval import Interval
from justthisonce import invariant

_COMPAT = [0]
_VERSION = 0

_METADATA_PATH = "metadata.sqlite3"
_PADDIR_PATHS = "pending", "current", "spent", "tmp"

class Error(Exception):
  """Base error for the pad module."""

class PathNotEmpty(Error):
  """The specified path is either a file or a non-empty directory."""

class InvalidPad(Error):
  """The on-disk pad structure has broken invariants, is corrupt, etc, and
     there is no obvious way to repair it."""

class PadNotFound(Error):
  """There is no file or directory at the specified path."""

class MissingPadfile(Error):
  """Padfile is either missing or a directory."""

class MultiplePadfileLinks(Error):
  """Specified padfile has additional hardlinks."""

class UnknownPadVersion(Error):
  """The on-disk pad is in an odd state but we can probably fix it safely."""

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
      interval = Interval.fromAtom(start, min(requested - len(alloc), length))
      seg = Allocation(self, interval)
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
  """Holds an allocation on the pad, which may contain multiple chunks in
     multiple files. They may be constructed with union-like updates."""
  __metaclass__ = invariant.EnforceInvariant

  def __init__(self, padfile=None, interval=None):
    """With no arguments, creates an empty allocation. With two, creates an
       allocation in the given file with the given interval (which must be
       non-empty)."""

    # Mapping from filename to (interval, padfile)
    self._alloc = collections.OrderedDict()
    self._size = 0

    if padfile is None or interval is None:
      assert padfile is None and interval is None
    else:
      self._alloc[padfile.filename] = (interval, padfile)
      self._size = len(interval)

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

  def toSerializationState(self):
    """Helper for the serialization code. This is a
       compromise between dumping internal logic code into message.py and dumping
       [potentially] legacy parsing code into pad.

       This provides an abstraction between the on-disk format and the internal
       representation. This format is a sequence of (filename, atoms) pairs
       where atoms is (start, length) pairs."""
    return (((filename, interval.toAtoms())
             for (filename, (interval, padfile))
             in self._alloc.iteritems()))

  @classmethod
  def fromSerializationState(klass, state):
    """See Allocation.toSerializationState"""
    self = klass()
    for (filename, atoms) in state:
      self.unionUpdate(Allocation(filename, Interval.fromAtoms(atoms)))
    return self 

  def __eq__(self, other):
    # Order matters!
    return self._size == other._size and self._alloc == other._alloc

  def __ne__(self, other):
    return not self.__eq__(other)

class Metadata(object):
  """Represents all metadata of the pad that is saved to disk."""

  def __init__(self):
    self.current = []
    self.compatability = COMPAT
    self.version = VERSION

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

  def __init__(self, db, paddir):
    self._db = db
    self._paddir = paddir

  def addPadfile(self, padfile, uuid=None, ignore_links=False):
    """Adds the specified padfile to the paddir. It will be moved there,
       possibly across devices, and add the necessare metadata. If
       ignore_links is False and the file has more than one hard link,
       raise MultiplePadfileLinks exception."""
    if not os.path.exists(padfile) or not os.path.isfile(padfile):
      raise MissingPadfile(padfile)

    stat_info = os.stat(padfile)
    if not ignore_links and stat_info.st_nlink != 1:
      raise MultiplePadfileLinks(padfile)

    basename = os.path.split(padfile)[1]
    if (os.path.exists(os.path.join(self._paddir, basename)) or
        self._db.execute("select count(id) from files where name=?;",
                         (basename,)).fetchone()[0] != 0:
      raise DuplicatePadfileName(basename)

    check_uuid_query = "select count(id) from files where uuid=?;"

    # If the user specifies an invalid uuid, we bail.
    if (uuid is not None and
        self._db.execute(check_uuid_query, (uuid,)).fetchone() != (0,)):
      raise DuplicateUUID(uuid)

    # Generate a unique uuid for the file.
    if uuid is None:
      uuid = uuidlib.uuid4()
      while self._db.execute(check_uuid_query, (uuid,)).fetchone() != (0,)):
        uuid = uuidlib.uuid4()

    # Move the padfile into the paddir. We use a tempname in case this is an
    # inter-device move, in which case it may be slow. We are not concerned with
    # malicious race conditions -- if an adversary can write to your paddir it's
    # already game over. The temp name is to prevent *accidental* overwrites.
    tmpname = os.path.join(self._paddir, "tmp", uuidlib.uuid4())
    while os.path.exists(tmpname):
      tmpname = os.path.join(self._paddir, "tmp", uuidlib.uuid4())
    os.rename(padfile, tmpname)

    # TODO: windows + old python will break this; figure out what to do.
    os.link(tmpname, destname)
    os.unlink(tmpname)

    # If the file copied correctly, add it to the database. To prevent potential
    # key material loss, we don't attempt to clean up once the move has started if
    # something should go wrong.
    self._db.execute("insert into files (name, uuid, size, dir, id) values (?,?,?,?,?);",
                     (basename, uuid, stat_info.st_size, "pending", None))
    self._db.commit()

  def _checkInvariant(self):
    pass

def createPad(path):
  """Creates a new empty pad at the specified path."""
  if os.path.exists(path):
    if not os.path.isdir(path) or os.listdir(path):
      raise PathNotEmpty()
  else:
    os.mkdir(path)

  dbpath = os.path.join(path, _METADATA_PATH)
  try:
    db = sqlite3.connect(dbpath)
    db.execute("pragma foreign_keys = ON;")
    db.execute("""create table files (
        name string not null unique,
        uuid string not null unique,
        size integer not null check(size >= 0),
        dir string check(dir in ('pending', 'current', 'spent')) not null,
        id integer not null unique primary key autoincrement);""")
    db.execute("""create table allocations (
        file integer not null references files(id),
        start integer not null check(start >= 0),
        length integer not null check(start >= 0));""")
    db.execute("pragma user_version=%i;" % _VERSION) # ? not ok with pragma.
    db.commit()
  except Exception:
    os.unlink(dbpath)
    raise

  for seg in _PADDIR_PATHS:
    os.mkdir(os.path.join(path, seg))

def loadPad(path):
  """Loads an existing pad at the given path."""
  if not os.path.exists(path):
    raise PadNotFound(path)
  if not os.path.isdir(path):
    raise InvalidPad("%s is not a directory." % path)
  for name in _PADDIR_PATHS:
    seg = os.path.join(path, name)
    if not os.path.exists(seg) or not os.path.isdir(seg):
      raise InvalidPad("Missing %s" % seg)
  dbfile = os.path.join(path, _METADATA_PATH)
  if not os.path.exists(dbfile) or not os.path.isfile(dbfile):
    raise InvalidPad("Missing %s" % dbfile)

  db = sqlite3.connect(dbfile)
  version = db.execute("pragma user_version;").fetchone()[0]
  if version not in _COMPAT:
    raise UnknownPadVersion("Pad version %i not supported. Supported: %s" % (version, _VERSION))

  return Pad(db, path)

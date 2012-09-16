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

class Allocation(object):
  """Holds an allocation on te pad, which may contain multiple chunks in
     multiple files. They may be constructed with union-like updates."""
  __metaclass__ = invariant.EnforceInvariant

  def __init__(self, padfile=None, start=None, length=None):
    """With no arguments, creates an empty allocation. With three, creates an
       allocation with a single interval."""

    # Mapping from filename to (padfile, intervals)
    self._alloc = collections.OrderedDict()
    self._size = 0

    if padfile is None or start is None or length is None:
      assert padfile is None and start is None and length is None
    else:
      self._alloc[padfile.filename] = (Interval.fromAtom(start, length), \
                                       padfile)
      self._size = length

  def _checkInvariant(self):
    assert self._size == sum((len(ival) for ival in self._alloc.itervalues()))

  def __len__(self):
    return self._size

  def union_update(self, other):
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
        post_merge[filename] = (ival, padfile)

    # Add in any files just in the other.
    map(merged.setdefault, other._alloc.iteritems())

    rval = Allocation()
    rval._size = self._size + other._size
    rval._alloc = merged
    return rval

  def iterFiles(self):
    """Returns an iterator of (interval, file)."""
    return self._alloc.itervalues()

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
    self._extents = Interval

    # Subdir the file is currently in.
    self._subdir = subdir

  def _checkInvariant(self):
    assert self.size >= self.used
    assert len(self._extents) == self.used

  @property
  def free(self):
    return self.size - self.used

  def getAllocation(self, requested):
    """Requests an allocation from the file of the given size. Raises OutOfPad
       if the file is out of space."""
    if requested > self.free:
      raise OutOfPad("File %i has %i bytes but you requested %i." % \
                     (self.filename, self.free, requested))

    alloc = Allocation()
    for (start, length) in self._extents.iterExterior(self.size):
      seg = Allocation(self, start, min(requested - len(alloc), length))
      alloc.union_update(seg)
      if len(alloc) >= requested:
        assert len(alloc) == requested
        break

    assert len(alloc) == requested
    return alloc

  def commitAllocation(self, ival):
    """Mark the specified interval as used. Error if overlaps with currently
       used area."""
    self._extents = self._extents.union(ival)

class Metadata(object):
  """Represents all metadata of the pad that is saved to disk."""

  def __init__(self):
    self.current = []
    self.compatability = None
    self.version = None

class Pad(object):
  """Represents an on-disk pad dir."""
  __metaclass__ = invariant.EnforceInvariant

  def __init__(self, path, create=False, fsck=False):
    """Opens a pad at the specified path. If create is True, will initialize
       the pad if it does not exist."""
    self._uncomitted = 0
    if not os.path.exists(path):
      if create:
        for subdir in "", "incoming", "current", "spent":
          os.mkdir("%s/%s" % (path, subdir))
        cPickle.dump(Metadata(), open("%s/metadata.pck" % path, 'w'), -1)
        open("%s/VERSION" % path, 'w').write("%s\n%s" % (COMPAT, VERSION))
      else:
        raise InvalidPad("No such file or directory: %s" % path)
    
    # Try to load the metadata
    try:
      self.metadata = cPickle.load(open("%s/metadata.pck" % path))
    except:
      raise InvalidPad("Metadata missing or corrupt")

    # Check the version and compatability
    try:
      self.metadata.compatability, self.metadata.version = \
          map(int, open("%s/VERSION" % path).read().split("\n"))
    except:
      raise InvalidPad("Version missing or corrupt")

    # Make sure the pad is compatable
    if self.metadata.compatability > COMPAT:
      raise InvalidPad("Pad is protocol %i but I only understand up to %i" % \
                       (self.metadata.compatability, COMPAT))

    # Verify directory structure and check for duplicate filenames.
    fn = []
    for subdir in "incoming", "current", "spent":
      if not os.path.exists("%s/%s" % (path, subdir)):
        raise InvalidPad("Directory structure bad")
      fn.extend(os.listdir("%s/%s" % (path, subdir)))
    if len(fn) != len(set(fn)):
      raise InvalidPad("Duplicate pad filenames detected. Filenames must be unique.")

    # Check for pads that are in metadata but not on-disk. If they
    # have any used space, their absence is an error but if not, they may
    # be stragglers left over from an interrupted "claiming" of a new
    # pad file, and we can savely remove their metadata.
    # TODO: Verify size during fsck
    for i in reversed(range(len(self.metadata.current))):
      entry = self.metadata.current[i]
      assert entry.subdir == "current"
      if not os.path.exists("%s/current/%s" % (path, entry.filename)):
        if entry.used in (0, entry.size):
          if not fsck:
            raise PadDirty("Unused or consumed pad %s found in current. This is probably ok." % entry.filename)
          del self.metadata.current[i]
        elif os.path.exists("%s/incoming/%s" % (path, entry.filename)):
          if not fsck:
            raise PadDirty("Entry %s found in incoming but expected in current." % entry.filename)
          entry.subdir = "incoming"
        elif os.path.exists("%s/spent/%s" % (path, entry.filename)):
          if not fsck:
            raise PadDirty("Pad found in spent but was not marked as used up in metadata.")
          del self.metadata.current[i]
        else:
          raise InvalidPad("Missing non-unused padfile %s" % entry.filename)

    # Verify the size of all pads that are in use
    for i in reversed(range(len(self.metadata.current))):
      entry = self.metadata.current[i]
      actual = os.stat("%s/current/%s" % (path, entry.filename))
      if entry.size != actual:
        if not fsck:
          raise InvalidPad("Current pad file %s changed size from %i to %i" % \
                           (entry.filename, entry.size, actual))
        # Can't trust it anymore. Mark it as spent but don't delete so can at least
        # try to decrypt later.
        os.rename(entry.path, "%s/spent/%s" % (path, entry.filename))
        del self.metadata.current[i]

    # Save the path
    self.path = path

    # Flush metadata if we were fscking
    if fsck:
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
    os.rename("%s/metadata.pck" % self.path, "%s/metadata.bkp" % self.path)
    os.rename("%s/VERSION" % self.path, "%s/VERSION.bkp" % self.path)
    cPickle.dump(self.metadata, open("%s/metadata.pck" % self.path, 'w'), -1)
    open("%s/VERSION" % self.path, 'w').write("%s\n%s" % (COMPAT, VERSION))

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
      new_pads = [(fn, os.stat("%s/incoming/%s" % (self.path, fn)).st_size) \
                  for fn in os.listdir("%s/incoming" % (self.path))]
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
      print "Allocating %i on %s" % (min(needed - len(allocation), pad.free), pad)
      newb = pad.getAllocation(min(needed - len(allocation), pad.free))
      allocation.union_update(newb)

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
        os.rename(padfile.path, "%s/current/%s" % (path, padfile.filename))
        padfile.subdir = "current"

      # Mark used extents as used in file, and move to spent if necessary
      padfile.markIntervalAsUsed(ival)
      if padfile.free == 0:
        os.rename(padfile.path, "%s/spent/%s" % (path, padfile.filename))
      
    # Write out the metadata
    self.flush()

  @property
  def uncommitted(self):
    return self._uncomitted

"""
The pad module is responsible for curating the store of pad material and
tracking use. The pad directory has three subdirs: incoming, current, and
spent.
"""

import cPickle
import os
import collections

import invariant

COMPAT = 0
VERSION = 0

class Error(Exception):
  """Base error for the pad module."""

class InvalidPad(Error):
  """The on-disk pad structure has broken invariants, is corrupt, etc."""

class OutOfPad(Error):
  """There is not enough pad remaining to allocate the requested range."""

class AllocationOutstanding(Error):
  """Cannot allocate another while one is outstanding."""

class Allocation(object):
  """Holds an allocation on te pad, which may contain multiple chunks in
     multiple files. They may be constructed with union-like updates."""
  __metaclass__ = invariant.EnforceInvariant

  def __init__(self, filename=None, start=None, length=None):
    """With no arguments, creates an empty allocation. With three, creates an
       allocation with a single interval."""

    # Mapping from filename to (start, length) list
    self._alloc = collections.OrderedDict()
    self._size = 0

    if filename is None or start is None or length is None:
      assert filename is None and start is None and length is None
    else:
      self._alloc.setdefault(filename, []).append((start, length))
      self._size = length

  def _checkInvariant(self):
    #TODO Consider somehow combining the overlap between Allocation and File,
    #     they have some similar logic with the extents. Keeping seperate for
    #     now since allocation holes have different semantic meaning and don't
    #     know their total underlying size.
    #
    #     Maybe decouple the logic for an interval type from semantic meaning?
    size = 0
    for (filename, extents) in self._alloc.iteritems():
      ptr = 0
      for (start, length) in extents:
        assert start >= ptr
        assert length > 0
        ptr = start + length
        size += length
    assert size == self._size

  def __len__(self):
    return self._size

  def union_update(self, other):
    """Combines two allocations, merging adjacent intervals. The allocations
       must not overlap, as there is never a good reason for this even though
       union is straightforward to compute either way. The result will have
       my files first, merged with the other's as appropriate, followed by the
       files just in the other."""
    post_merge = collections.OrderedDict()
    for (filename, extents) in self._alloc.iteritems():
      if filename in other._alloc:
        # Need to merge intervals
        self_i = other_i = 0

        # The current open interval
        start_cur = 0
        length_cur = 0

        # Walk all intervals in order of start.
        while self_i < len(self._alloc[filename]) or \
              other_i < len(other._alloc[filename]):
          if self_i < len(self._alloc[filename]) and \
             (other_i == len(self._alloc[filename]) or \
             self._alloc[filename][self_i] < other._alloc[filename][other_i]):
            start, length = self._alloc[filename]
            self_i += 1
          else:
            start, length = other._alloc[filename]
            other_i += 1

          # Intervals may not overlap.
          assert start >= start_cur + length_cur

          if start == start_cur + length_cur:
            # We can merge this with the current interval.
            length_cur += length
          else:
            # There was a skip so we need to save the old current and start
            # a new one.
            post_merge[filename].append((start_cur, length_cur))
            start_cur, length_cur = start, length

        # Don't forget to push the final interval, if applicable
        if length_cur > 0:
          post_merge[filename].append((start_cur, length_cur))

      else:
        post_merge[filename] = extents

    for (filename, extents) in other._alloc.iteritems():
      if filename not in self._alloc:
        post_merge[filename] = extents

    self._size = self._size + other._size
    self._alloc = post_merge

class File(object):
  """Holds data on what parts of a file have already been used."""
  __metaclass__ = invariant.EnforceInvariant

  def __init__(self, filename, size):
    # Total size of the file
    self.size = size

    # Number of bytes in the file that have been used already.
    self.used = 0

    # Relative name of the file.
    self.filename = filename

    # Regions of the file in use. Must be non-overlapping and sorted.
    self._extents = []

  def _checkInvariant(self):
    assert self.size >= self.used
    # Yes, this is O(n). However remember that there will seldom, if ever, be
    # more than a few extents.
    ptr = 0
    used = 0
    for (start, length) in self._extents:
      assert start >= ptr
      assert length > 0
      used += length
      ptr = start + length
    assert used == self.used

  def getAllocation(self, requested):
    """Requests an allocation from the file of the given size. Raises OutOfPad
       if the file is out of space."""
    if requested > self.free:
      raise OutOfPad("File %i has %i bytes but you requested %i." % \
                     (self.filename, self.free, requested))

    ptr = 0
    alloc = Allocation()
    for (start, length) in self._extents:
      if start > ptr:
        seg = Allocation(self.filename, start, \
                         min(requested - len(alloc), start - ptr))
        alloc.union_update(seg)
        ptr = start + length
      if len(alloc) >= requested:
        break
    else:
      seg = Allocation(self.filename, ptr, \
                       min(requested - len(alloc), self.size - ptr))
      alloc.union_update(seg)

    assert len(alloc) == requested
    return alloc
    
  @property
  def free(self):
    return self.size - self.used

class Metadata(object):
  """Represents all metadata of the pad that is saved to disk."""

  def __init__(self):
    self.current = []
    self.compatability = None
    self.version = None

class Pad(object):
  """Represents an on-disk pad dir."""
  __metaclass__ = invariant.EnforceInvariant

  def __init__(self, path, create=False):
    """Opens a pad at the specified path. If create is True, will initialize
       the pad if it does not exist."""
    s._uncomitted = 0
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
      raise
      raise InvalidPad("Version missing or corrupt")

    # Make sure the pad is compatable
    if self.metadata.compatability > COMPAT:
      raise InvalidPad("Pad is protocol %i but I only understand up to %i" % \
                       (self.metadata.compatability, COMPAT))

    # Verify directory structure 
    for subdir in "incoming", "current", "spent":
      if not os.path.exists("%s/%s" % (path, subdir)):
        raise InvalidPad("Directory structure bad")

    # Check for pads that are in metadata but not on-disk. If they
    # have any used space, their absence is an error but if not, they may
    # be stragglers left over from an interrupted "claiming" of a new
    # pad file, and we can savely remove their metadata.
    for i in reversed(range(len(self.metadata.current))):
      entry = self.metadata.current[i]
      if not os.path.exists("%s/current/%s" % (path, entry.filename)):
        if entry.used == 0:
          del self.metadata.current[i]
        else:
          raise InvalidPad("Missing non-unused padfile %s" % entry.filename)

    # Verify the size of all pads that are in use
    for entry in self.metadata.current:
      actual = os.stat("%s/current/%s" % (path, entry.filename))
      if entry.size != actual:
        raise InvalidPad("Current pad file %s changed size from %i to %i" % \
                         (entry.filename, entry.size, actual))

    # Save the path
    self.path = path

  def _checkInvariant(self):
    assert s._uncomitted in (0, 1)

  def flush(self):
    """Flush the pad's current state to disk but do not close it. This will
       not discard uncommitted transactions, but they will not be saved to
       disk. This is intentional -- If we crash before a txn is explicitly
       committed, it should be rolled back."""
    # Save old as a backup in case the dump fails. Routines that move the
    # actual files around should be able to tolerate reverting to these if
    # flush/close raises an exception.
    os.rename("%s/metadata.pck" % self.path, "%s/metadata.bkp" % self.path)
    os.rename("%s/VERSION" % self.path, "%s/VERSION.bkp" % self.path)
    cPickle.dump(self.metadata, open("%s/metadata.pck" % self.path, 'w'), -1)
    open("%s/VERSION" % self.path, 'w').write("%s\n%s" % (COMPAT, VERSION))

  def getAllocation(self, requested):
    """Requests the pad to allocate requested bytes of pad. Returns an
       Allocation or raises OutOfPad if there is no pad left. This can claim
       pads in incoming (and will move them and sync the metadata), but
       will not itself mark pads used."""
    # Look through the files we are already using first.
    current_free = sum((pad.free for pad in self.metadata.current))

    if current_free < requested:
      # We need more pad. Look through incoming to see if we can service the
      # request, beginning with the smallest files.
      can_get = 0
      new_pads = [(fn, os.stat("%s/incoming/%s" % (self.path, fn)).st_size) \
                  for fn in os.listdir("%s/incoming" % (self.path))]
      new_pads.sort(lambda (pad, size): size)
      for last_need, (pad, size) in enumerate(new_pads):
        can_get += size
        if can_get + current_free >= requested:
          break
      else:
        raise OutOfPad("Can't allocate %i bytes; %i bytes available" \
                       % (requested, can_get))

      # Move the pads we need into current. We add all the new metadata
      # first and flush to disk before moving files, since init code
      # will silently remove metadata which have missing files and
      # no used sections.
      new_files = [File(pad, size) for (pad, size) in new_pads[:last_need + 1]]
      self.metadata.current.extend(new_files)
      
      # Write out the metadata
      self.flush()

      # Move the files
      for f in new_files:
        #TODO: os.rename is not guaranteed to be atomic on Windows iirc. Should
        # look into this if I want to support windows later.
        os.rename("%s/incoming/%s" % (self.path, f.filename), \
                  "%s/current/%s" % (self.path, f.filename))

    # There is now enough space to actually allocate in current.
    needed = requested
    allocation = Allocation()
    for pad in self.metadata.current:
      print "Allocating %i on %s" % (min(needed - len(allocation), pad.free), pad)
      newb = pad.getAllocation(min(needed - len(allocation), pad.free))
      allocation.union_update(newb)

    assert len(allocation) == requested
    s._uncomitted += 1
    return allocation

  def discardUncommitted(self):
    """Releases any outstanding allocations."""
    assert self._uncomitted == 1
    self._uncomitted = 0
  
  def commitAllocation(self, alloc):
    """Commits the use of an allocation, and flushes the updated pad to disk"""
    assert self._uncomitted == 1
    self._uncomitted = 0
    #TODO write
  
  @property
  def uncommitted(self):
    return self._uncomitted

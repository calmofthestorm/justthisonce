"""
Provides the Interval class for describing integer intervals on a numberline.
"""

import invariant

class Interval(object):
  """Provides the Interval class for describing integer intervals on a
     numberline."""
  __metaclass__ = invariant.EnforceInvariant

  def __init__(self):
    """Creates an empty interval"""
    self._size = 0
    self._extents = ()

  @classmethod
  def fromAtom(klass, start, length):
    """Factory method that creates an interval consisting only of one piece
       of specified start and length. Length must be >= 0."""
    atom = Interval()
    if length != 0:
      atom._extents = ((start, length),)
    atom._size = length
    atom._checkInvariant()
    return atom

  @classmethod
  def fromAtoms(klass, atoms):
    """Factory method that creates an interval consisting of the specified
       (start, length) pairs. They need not be sorted and zero-length atoms
       are allowed, but all atoms must be disjoint."""
    atom = Interval()
    atom._extents = tuple(sorted([a for a in atoms if a[1] != 0]))
    if not atom._extents:
      atom._size = 0
    else:
      atom._size = sum(zip(*atom._extents)[1])

    # We need to canonicalize any adjacent user inputs.
    atom = atom.union(Interval())
    atom._checkInvariant()
    return atom

  def _checkInvariant(self):
    assert self._size >= 0
    assert type(self._extents) is tuple
    ptr = 0
    used = 0
    for (start, length) in self._extents:
      assert start >= ptr
      assert length > 0
      used += length
      ptr = start + length
    assert used == self._size

  def __len__(self):
    return self._size

  def __eq__(self, other):
    return self._extents == other._extents

  def __ne__(self, other):
    return not self.__eq__(other)

  def toAtoms(self):
    """Converts the interval to a series of (start, length) pairs which are
       guaranteed not to overlap."""
    return tuple(self._extents)

  def iterInterior(self):
    """Returns an iterator over chunks of the interval that are "inside" the
       interval, as (start, length) pairs."""
    return iter(self._extents)

  def iterExterior(self, total_length=None):
    """Returns an iterator over chunks of the interval that are "outside" the
       interval, as (start, length) pairs. This is essentially iterating the
       complement of the interval, and as such needs to know the universe. We
       assume that all universes start at 0, but do not know their length.
       If total_length is provided, the iterator will (if appropriate) return a
       chunk from the final piece of the interval to the end. If it is none,
       then the interval is assumed to end at the final chunk of the interval.
       If given, total_length must be greater than the largest item in the
       interval."""
    ptr = 0
    for (start, length) in self._extents:
      if start > ptr:
        yield (ptr, start - ptr)
      ptr = start + length

    assert total_length is None or total_length >= ptr
    if total_length is not None and ptr < total_length:
      yield (ptr, total_length - ptr)

  def union(self, other):
    """Returns a new interval that is the union of the two supplied.
       The arguments must be disjoint."""
    # Need to merge intervals
    self_i = other_i = 0

    # The current open interval
    start_cur = 0
    length_cur = 0

    merged = []
    merged_size = 0
    # Walk all intervals in order of start.
    while self_i < len(self._extents) or \
          other_i < len(other._extents):
      if self_i < len(self._extents) and \
         (other_i == len(other._extents) or \
         self._extents[self_i] < other._extents[other_i]):
        start, length = self._extents[self_i]
        self_i += 1
      else:
        start, length = other._extents[other_i]
        other_i += 1

      # Intervals may not overlap.
      assert start >= start_cur + length_cur

      if start == start_cur + length_cur:
        # We can merge this with the current interval.
        length_cur += length
      else:
        # There was a skip so we need to save the old current and start
        # a new one.
        if length_cur > 0:
          merged.append((start_cur, length_cur))
        start_cur, length_cur = start, length
      merged_size += length

    # Don't forget to push the final interval, if applicable
    if length_cur > 0:
      merged.append((start_cur, length_cur))

    rval = Interval()
    rval._extents = tuple(merged)
    rval._size = merged_size
    return rval
 
  def min(self):
    """Returns the smallest value in the interval. If the interval is empty,
       returns None."""
    if not self._extents:
      return None
    else:
      return self._extents[0][0]
 
  def max(self):
    """Returns the largest value in the interval. If the interval is empty,
       returns None."""
    if not self._extents:
      return None
    else:
      return sum(self._extents[-1]) - 1

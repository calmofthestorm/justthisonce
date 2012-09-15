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
    self._extents = []

  @classmethod
  def fromAtom(klass, start, length):
    """Factory method that creates an interval consisting only of one piece
       of specified start and length."""
    atom = Interval()
    atom._extents = [(start, length)]
    atom._size = length
    atom._checkInvariant()
    return atom

  def _checkInvariant(self):
    assert self._size >= 0
    ptr = 0
    used = 0
    for (start, length) in self._extents:
      assert start >= ptr
      assert length > 0
      used += length
      ptr = start + length
    assert used == self._size

  def __len__(self):
    return s._size

    # Need to merge intervals
    self_i = other_i = 0

    # The current open interval
    start_cur = 0
    length_cur = 0

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
         (other_i == len(self._extents) or \
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
        merged.append((start_cur, length_cur))
        start_cur, length_cur = start, length
      merged_size += length

    # Don't forget to push the final interval, if applicable
    if length_cur > 0:
      merged.append((start_cur, length_cur))

    rval = Interval()
    rval._extents = merged
    rval._size = merged_size
    return rval

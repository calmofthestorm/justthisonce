"""
Code for processing messages themselves (as well as notifications etc). All
[de] serialization is handled here, rather than in the classes they operate on,
because I don't want to mix parsing with the actual program logic.
"""

import re

COMPATIBILITY = 0
MAGIC = "JustThisOnceMessage"

#TODO: make app-wide and agree with pad.py
VERSION = 0

class Error(Exception):
  pass

class BadMessage(Error):
  pass

class Message(object):
  """Represents all metadata of a message that is not encrypted. We avoid
     pickle for the messages themselves as it trivially allows exection of
     arbitrary code."""
  _REGEX = re.compile("%s\nCompatibility (\d+)\nLength (\d+)\nVersion (\d+)\n"
                     % MAGIC)

  def __init__(self, alloc, crypttext_length, crypttext_sha=None):
    self.allocation = alloc
    self.compatibility = COMPATIBILITY
    self.version = VERSION
    self.length = crypttext_length

  def serialize(self):
    """Convert to a format suitable for open interchange."""
    rval = ("%s\nCompatibility %i\nLength %i\nVersion %i\n" %
            (MAGIC, self.compatibility, self.length, VERSION))
    for (filename, atoms) in self.allocation.get_serialization_state():
      atom_string = ", ".join(("%i %i" % atom) for atom in atoms)
      rval += "\t%s\x00%s\n" % (filename, atom_string)
    return rval

  @classmethod
  def deserialize(klass, msg):
    """Read a message's metadata from disk."""
    self = klass()
    match = _REGEX.match(msg)
    if not match:
      raise BadMessage("Can't parse message.")

    self.compatibility, self.length, self.version = match.groups()
    self.allocation = pad.Allocation.deserialize(msg[match.end():])

    return self

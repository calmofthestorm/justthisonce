"""
Code for processing messages themselves (as well as notifications etc). All
[de] serialization is handled here, rather than in the classes they operate on,
because I don't want to mix parsing with the actual program logic.
"""

import json
import pad
import sha

COMPATIBILITY = 0
MAGIC = "JustThisOnceMessage"

#TODO: make app-wide and agree with pad.py
VERSION = 0

class Error(Exception):
  pass

class BadMessage(Error):
  pass

class FutureMessageFormat(Error):
  pass

class Message(object):
  """Represents all metadata of a message that is not encrypted. We avoid
     pickle for the messages themselves as it trivially allows execution of
     arbitrary code."""
  _KEYS = "allocation", "compatibility", "version", "length", "hash"
  _HASH_PLACEHOLDER = sha.sha().hexdigest()

  def __init__(self, alloc, payload_length, payload_hash=_HASH_PLACEHOLDER,
               data = None):
    self.allocation = alloc
    self.compatibility = COMPATIBILITY
    self.version = VERSION
    self.length = payload_length
    self.hash = payload_hash
    self.data = {} if data is None else data

  def toJSON(self):
    """Convert to a format suitable for open interchange."""
    data = {}
    for key in self._KEYS:
      data[key] = getattr(self, key)
    data["allocation"] = data["allocation"].toSerializationState()
    data = json.dumps(data)
    return str(len(data)) + "\n" + data

  @classmethod
  def fromJSON(klass, string_or_fd):
    """Read a message's metadata from disk. Does minimal validation."""
    self = klass()
    if isinstance(string_or_fd, basestring):
      string_or_fd = StringIO.StringIO(string_or_fd)
    data = json.loads(string_or_fd.read(int(string_or_fd.readline())))
    try:
      self.compatibility = data["compatibility"]
      if self.compatibility > COMPATIBILITY:
        raise FutureMessageFormat(self.compatibility)
      for key in self._KEYS:
        setattr(self, key, data[key])
      for (key, value) in data.iteritems():
        if key not in self._KEYS:
          self.data[key] = value
    except KeyError:
      raise BadMessage("Missing required keys.")

    self.allocation = pad.Allocation.fromSerializationState(data["allocation"])

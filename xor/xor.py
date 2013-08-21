import ctypes
import cxorlib
import sys
import os

try:
  # TODO: this needs to be relative to application dir.
  _xorlib=ctypes.cdll.LoadLibrary("/home/alexr/projects/justthisonce/xor/cxor.so")
except Exception:
  sys.stderr.write("Error loading C XOR library; falling back to (slow) Python.")
  _xorlib = None

class Error(Exception):
  pass

class AllocationSizeMismatch(Error):
  pass

class CXORError(Error):
  pass

def execute(fxn, *args):
  if fxn(*args) != 0:
    raise CXORError()

class PyXOR(object):
  """Pure Python implementation of the CXOR interface. Used both for testing and
     as an option should the C implementation be unavailable."""
  BUFFER_LENGTH = 4 * 1024 * 1024
  class PyXORWorkUnit(object):
    def __init__(self):
      self.inputs = [None, None]
      self.output = None

  @staticmethod
  def execute_open_input(work, index, filename):
    if work.inputs[index] and work.inputs[index] != sys.stdin:
      work.inputs[index].close()
    if filename:
      work.inputs[index] = open(filename, "rb")
    elif work.inputs[0 if index == 1 else 1] != sys.stdin:
      work.inputs[index] = sys.stdin
    else:
      execute_cleanup(work)
      return -1
    return 0

  @staticmethod
  def execute_open_output(work, filename):
    if work.output and work.output != sys.stdout:
      work.output.close()
    if filename:
      work.output = open(filename, "ab")
    else:
      work.output = sys.stdout
    return 0

  @staticmethod
  def execute_seek_input(work, index, pos):
    if not work.inputs[index] or work.inputs[index] == sys.stdin:
      execute_cleanup(work)
      return -1
    work.inputs[index].seek(ps, os.SEEK_SET)

  @staticmethod
  def execute_xor(work, length):
    while length > 0:
      size = min(length, BUFFER_LENGTH)
      length -= size

      data = zip(work.inputs[i].read(size) for i in xrange(2))
      if len(data) != size:
        execute_cleanup(work)
        return -1
      work.output.write(chr(ord(a) ^ ord(b)) for (a, b) in data)

  @staticmethod
  def execute_cleanup(work):
    for fd in [work.output] + work.inputs:
      if fd not in (None, sys.stdin, sys.stdout):
        fd.close()
    work.output = work.inputs[0] = work.inputs[1] = None

def xorAllocation(alloc, infile, outfile, impl="C"):
  """Given an allocation and an input file, xor the allocation with the input
     file and *append* the result to the specified output file. infile and/or
     outfile should be None to indicate stdin/stdout."""
  if impl == "Python" or _xorlib is None:
    xor = PyXOR
    work = PyXOR.PyXORWorkUnit()
  elif impl == "C":
    xor = _xorlib 
    work = cxorlib.XorWorkUnit()
  else:
    raise Error("Unknown encryption provider: %s" % impl)

  # Check the allocation is the correct length.
  infile_size = os.stat(infile).st_size
  if infile_size != len(alloc):
    raise AllocationSizeMismatch(os.stat(infile), len(alloc))

  work.output = None
  work.inputs[0] = None
  work.inputs[1] = None

  try:
    execute(xor.execute_open_input, work, 1, infile)
    execute(xor.execute_open_output, work, outfile)

    # Encrypt the allocation one interval at a time.
    for (pad_interval, pad_file) in alloc.iterValues():
      execute(xor.execute_open_input, work, 0, pad_file)
      for (start, length) in pad_interval.toAtoms():
        execute(xor.execute_seek_input, work, 0, start)
        execute(xor.execute_xor, work, length)
    execute(xor.execute_cleanup, work)
  except AssertionError:
    raise CXORError()

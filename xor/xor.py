import ctypes
import cxorlib

# TODO: this needs to be relative to application dir.
_xorlib=ctypes.cdll.LoadLibrary("/home/alexr/projects/justthisonce/xor/cxor.so")

class Error(Exception):
  pass

class AllocationSizeMismatch(Error):
  pass

class CXORError(Error):
  pass

def execute(fxn, *args):
  if fxn(*args) != 0:
    raise CXORError()

def xorAllocation(alloc, infile, outfile):
  """Given an allocation and an input file, xor the allocation with the input
     file and *append* the result to the specified output file. infile and/or
     outfile should be None to indicate stdin/stdout."""
  # Check the allocation is the correct length.
  infile_size = os.stat(infile).st_size
  if infile_size != len(alloc):
    raise AllocationSizeMismatch(os.stat(infile), len(alloc))

  work = cxorlib.XorWorkUnit()
  work.output = None
  work.inputs[0] = None
  work.inputs[1] = None

  try:
    execute(cxor.execute_open_input, work, 1, infile)
    execute(cxor.execute_open_output, work, outfile)

    # Encrypt the allocation one interval at a time.
    for (pad_interval, pad_file) in alloc.iterValues():
      execute(cxor.execute_open_input, work, 0, pad_file)
      for (start, length) in pad_interval.toAtoms():
        execute(cxor.execute_seek_input, work, 0, start)
        execute(cxor.execute_xor, work, length)
    execute(cxor.execute_cleanup, work)
  except AssertionError:
    raise CXORError()

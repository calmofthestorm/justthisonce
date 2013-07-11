import ctypes
import cxorlib

_xorlib=ctypes.cdll.LoadLibrary("./cxor.so")

class Error(Exception):
  pass

class AllocationSizeMismatch(Error):
  pass

class CXORError(Error):
  pass

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
    assert(!cxor.execute_open_input(work, 1, infile))
    assert(!cxor.execute_open_output(work, outfile))

    # Encrypt the allocation one interval at a time.
    for (pad_interval, pad_file) in alloc.iterValues():
      assert(!cxor.execute_open_input(work, 0, pad_file))
      for (start, length) in pad_interval.toAtoms():
        assert(!cxor.execute_seek_input(work, 0, start))
        assert(!cxor.execute_xor(work, length))
    assert(!cxor.execute_cleanup(work))
  except AssertionError:
    raise CXORError()

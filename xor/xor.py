import ctypes
import cxorlib


old = """
# TODO: see about auto-extracting the data structures/enums from shared source
# TODO: consider moving to true Python bindings (but this complicates the build
#       dramatically; may not be worth it for end users)

class _Range(ctypes.Structure):
  _fields = [("start", ctypes.c_size_t),
             ("length", ctypes.c_size_t)]

class _File(ctypes.Structure):
  _fields_ = [("n_ranges", ctypes.c_size_t),
              ("filepath", ctypes.c_char_p),
              ("ranges", ctypes.c_void_p),
              ("fd", ctypes.c_void_p),
              ("size", ctypes.c_size_t)]
              ("range_left", ctypes.c_size_t)]
              ("cur_range", ctypes.c_size_t)]

class _XorResult(object):
  SUCCESS = 0
  NO_WORK = 1
  SIZE_MISMATCH = 2
  OUTFILE_ERROR = 3
  INFILE_ERROR = 4
  MALLOC_FAILED = 5
  INVALID_RANGE = 6
  INFILE_SEEK_ERROR = -1
  OUTFILE_SEEK_ERROR = -2
"""

_xorlib=ctypes.cdll.LoadLibrary("./cxor.so")

def xorFiles(files, outfile):
  """Given files (a sequence of pairs of (filename, interval)), xor the
     specified ranges together and write it to outfile, itself a pair of
     (filename, interval)."""
  # Filenames must occur at most once.
  filenames = (outfile[0],) + zip(*files)[0]
  assert len(filenames) == len(set(filenames))

  # Verify that all files ranges have same length.
  assert len(set(len(interval) for (_, interval) in [outfile] + files)) == 1

  # Create C data structures
  def makeFile_t(element):
    filepath, interval = element
    atoms = interval.toAtoms()
    ranges = (cxorlib.Range_t * len(atoms))()
    for i, atom in enumerate(atoms):
      ranges[i].start, ranges[i].length = atom
    return cxorlib.File_t(len(ranges), filepath, ranges)

  c_files = (cxorlib.File_t * len(files))()
  for i, infile in enumerate(files):
    c_files[i] = makeFile_t(infile)
  
  c_outfile = makeFile_t(outfile)
  return _xorlib.xor_files(c_files, len(files), ctypes.pointer(c_outfile))

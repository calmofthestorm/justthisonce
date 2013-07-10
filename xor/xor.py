import ctypes
import cxorlib

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

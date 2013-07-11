import ctypes
import cxorlib

_xorlib=ctypes.cdll.LoadLibrary("./cxor.so")

class Error(Exception):
  pass

class AllocationSizeMismatch(Error):
  pass

def xorAllocation(alloc, infile, outfile):
  """Given an allocation and an input file, xor the allocation with the input
     file and *append* the result to the specified output file. All files
     must be seekable."""
  # Check the allocation is the correct length.
  infile_size = os.stat(infile).st_size
  if infile_size != len(alloc):
    raise AllocationSizeMismatch(os.stat(infile), len(alloc))

  # Encrypt the allocation one interval at a time.
  infile_offset = 0
  if os.path.exists(outfile):
    outfile_offset = os.stat(outfile).st_size
  else:
    outfile_offset = 0
  for (pad_interval, pad_file) in alloc.iterValues():
    # Create intervals for the input and output files, which are just being
    # processed sequentially.
    infile_interval = Interval.fromAtom(infile_offset, len(pad_interval))
    outfile_interval = Interval.fromAtom(outfile_offset, len(pad_interval))
    infile_offset += len(pad_interval)
    outfile_offset += len(pad_interval)

    # Process this interval
    _xorFiles([(infile, infile_interval), (pad_file, pad_interval)],
              (outfile, outfile_interval))

def _xorFiles(files, outfile):
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
  res = _xorlib.xor_files(c_files, len(files), ctypes.pointer(c_outfile))
  if res:
    raise CXORError(res)

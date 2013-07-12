"""
Main interface module containing externally-visible functions. Used by justonce,
but also potentially available to other programs.
"""

import math
import os
import uuid as uuidlib
import xor.xor

import justthisonce.pad

BLOCKSIZE = 4 * 1024 * 1024

class OneTimePad(object):
  def __init__(self, path, create=False):
    """Loads (or creates, if create=True), the pad located at path."""
    self._path = path
    if create:
      self._pad = justthisonce.pad.createPad(path)
    else:
      self._pad = justthisonce.pad.loadPad(path)

  def generatePad(numBytes, numFiles=1, urandom=True):
    """Generates numFiles new pad files each of size numBytes using
       /dev/random (or /dev/urandom if urandom=True). Returns a list of
       the files created. Note that without specialized hardware /dev/random
       will be obscenely slow for any non-tiny files, therefore the default
       is to use urandom, on which a cryptanalytic attack is theoretically
       possible, though not known in the non-classified literature."""
    if numBytes <= 0 or numFiles < 0:
      raise ValueError("Need non-negative number of files of positive size.")
  
    rng = "/dev/urandom" if urandom else "/dev/random"
    count = math.ceil(numBytes / BLOCKSIZE)
    new_files = []
    for i in range(numFiles):
      uuid = uuidlib.uuid4()
      while os.path.exists("%s/incoming/%s" % (self._path, uuid)):
        uuid = uuidlib.uuid4()
      cmd = "dd if=%s of=%s/incoming/%s bs=%i count=%i 2> /dev/null > /dev/null"
      if 0 != os.system(cmd % (rng, self._path, uuid.uuid4(), BLOCKSIZE, count)):
        raise IOError("DD error.")
      new_files.append("%s/incoming/%s" % uuid)

  def encryptFile(infile, outfile, size=None):
    """Encrypts the input file at infile using the pad to outfile. Either/both
       may be None to use stdin/stdout. If encrypting from stdin, size is the
       block size to use. (Currently, partial blocks are consumed when
       encrypting from stdin.) Writes the raw bytes out to the outflie and
       the metadata is returned as a string."""
    if size < 0:
      raise ValueError("size must be >= 0.")

    if size is None:
      size = BLOCKSIZE


    if infile is None:
      # TODO: reclaim the non-used portion of the final alloc.
      data_length = 0
      total_alloc = alloc = self._pad.getAllocation(size)
      self._pad.commitAllocation(alloc)
      count = xor.xor.xorAllocation(alloc, infile, outfile)
      data_length += count
      while count == len(alloc):
        alloc = self._pad.getAllocation(size)
        self._pad.commitAllocation(alloc)
        total_alloc.unionUpdate(alloc)
        count = xor.xor.xorAllocation(alloc, infile, outfile)
        data_length += count
      alloc = total_alloc
    else:
      data_length = os.stat(infile).st_size
      alloc = self._pad.getAllocation(data_length)
      self._pad.commitAllocation(alloc)
      # Because we don't know whether a partial file may be readable, we commit
      # the allocation before attempting encryption. It may be rolled back later
      # if the user is sure it is safe to do so.
      assert xor.xor.xorAllocation(alloc, infile, outfile) == len(alloc)

    # Create the decryption message metadata.
    return justthisonce.Message(alloc, data_length).toJSON()

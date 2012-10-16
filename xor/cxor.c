#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <assert.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/stat.h>

const int BUFFER_LENGTH = 4 * 1024 * 1024;

static inline size_t min(size_t a, size_t b) {
  return a > b ? b : a;
}

/* Keep reading until you get all the bytes. */
void readbuf(char* buffer, int file, size_t chunk) {
  while (chunk > 0) {
    int res = read(file, buffer, chunk);
    assert(res >= 0);
    buffer += res;
    chunk -= res;
  }
}

/* Keep writing until done. */
void writebuf(char* buffer, int file, size_t chunk) {
  while (chunk > 0) {
    int res = write(file, buffer, chunk);
    assert(res >= 0);
    buffer += res;
    chunk -= res;
  }
}

/* Structure to represent a single range in a single file to xor. */
typedef struct {
  size_t start;
  size_t length;
} Range_t;

/* Structure to represent ranges in a file. It is acceptable for ranges
   to overlap because checking for this in C is complex. */
typedef struct {
  size_t n_ranges;
  char* filepath;
  Range_t* ranges;
  /* used internally */
  FILE* fd;
  char* buffer;
  size_t size;
  size_t range_left; /* Number of bytes in current range left */
  size_t cur_range;  /* Index of current range */
} File_t;

/* REQUIRES: file points to a valid file structure.
   RETURNS:  the total size of all ranges in the file. Overlapping segments
             are counted multiple times. */
size_t get_total_size(const File_t* file) {
  size_t total = 0;
  size_t i;

  for (i = 0; i < file->n_ranges; ++i) {
    total += file->ranges[i].length;
  }
  return total;
}

typedef enum {SUCCESS=0, NO_WORK, SIZE_MISMATCH, OUTFILE_ERROR,
              INFILE_ERROR, MALLOC_FAILED, INVALID_RANGE,
              INFILE_SEEK_ERROR=-1, OUTFILE_SEEK_ERROR=-2} XorResult;

/* REQUIRES: all file objects completely valid.
   MODIFIES: the buffers and files open by the fds in the file objects
   RETURNS:  SUCCESS (0) */
XorResult xor_worker(File_t inputs[], size_t n_inputs, File_t* output) {
  size_t remaining = 0;
  size_t i;

  /* Populate the ranges. */
  output->cur_range = 0;
  output->range_left = output->ranges[0].length;
  for (i = 0; i < n_inputs; ++i) {
    /* Begin at the first range, seek to it, and remember we have all of it
       left. remaining should be the min of them all. */
    inputs[i].cur_range = 0;
    inputs[i].range_left = inputs[i].ranges[0].length;
    if (fseek(inputs[i].fd, inputs[i].ranges[0].start, SEEK_SET)) {
      return INFILE_SEEK_ERROR;
    }
  }

  while (1) {
    /* Read through all ranges in file. */
    while (output->range_left == 0 && ++output->cur_range < output->n_ranges) {
      output->range_left = output->ranges[output->cur_range].length;
      if (fseek(output->fd, output->ranges[output->cur_range].start,
          SEEK_SET)) {
        return OUTFILE_SEEK_ERROR;
      }
    }
    if (output->cur_range == output->n_ranges) {
      return SUCCESS;
    }
    remaining = output->cur_range;
    for (i = 0; i < n_inputs; ++i) {
      while (inputs[i].range_left == 0 && ++inputs[i].cur_range) {
        inputs[i].range_left = inputs[i].ranges[inputs[i].cur_range].length;
        if (fseek(inputs[i].fd, inputs[i].ranges[inputs[i].cur_range].start,
                  SEEK_SET)) {
          return INFILE_SEEK_ERROR;
        }
      }
      if (inputs[i].cur_range == inputs[i].n_ranges) {
        return SUCCESS;
      }
      remaining = min(remaining, inputs[i].range_left);
    }

    /* Proceed as far as we can with what is currently remaining. */
    while (remaining > 0) {
      /* TODO: decouple buffers from ranges to improve performance. */
      size_t len = min(remaining, BUFFER_LENGTH);

      /* Read in the data we need from all files. */
      /* TODO: we only need 2 buffers; not n+1 */
      if (fread(output->buffer, 1, len, inputs[0].fd) != len) {
        return INFILE_SEEK_ERROR;
      }
      for (i = 1; i < n_inputs; ++i) {
        if (fread(inputs[i].buffer, 1, len, inputs[i].fd) != len) {
          return INFILE_SEEK_ERROR;
        }
      }

      /* Perform the encryption. */
      for (i = 1; i < n_inputs; ++i) {
        int j;
        for (j = 0; j < len; ++j) {
          ((int*)output->buffer)[j] ^= ((int*)inputs[i].buffer)[j];
        }
      }

      /* Write to the outfile */
      fwrite(output->buffer, 1, len, output->fd);

      /* Keep track of progress */
      assert(len <= remaining);
      remaining -= len;
    }
  }
}

/* REQUIRES: files is either null or a n_files long valid array of valid File_t
             structs. outfile is null or a valid File_t. no files in files ore
             modified on disk during the call. cleanup is caller's
             responsibility if the return value is negative. no file occurs in
             files more than once, outfile does not occur in files, and
             ranges in outfile do not overlap.
   MODIFIES: overwrites (and ignores) all files fd and buffer members.
   EFFECTS:  will verify that all files have the same length (sum of their
             ranges) and that all ranges are valid. If all conditions are met,
             proceeds through the ranges in each file, computing the parity of
             each bit and storing it in the corresponding range in outfile,
             which will be created if it does not exist and truncated if it
             does.
   RETURNS:  an appropriate error code from the XorResult enum. 0 will always
             indicate success, positive values indicate a warning, negative
             values indicate an error and that cleanup may be necessary. */
XorResult xor_files(File_t files[], const size_t n_files,
                    File_t* outfile) {
  size_t i;

  /* Total size of the range to xor. */
  size_t total_size = get_total_size(outfile);

  /* Buffers to do the actual copy. */
  char* buffer_memory = NULL;

  /* Return value */
  XorResult rval;

  /* Not an error but no work to do. */
  if (!outfile || !files || n_files == 0) {
    return NO_WORK;
  }

  /* Verify that all files have the same total size. */
  for (i = 0; i < n_files; ++i) {
    if (total_size != get_total_size(&files[i])) {
      return SIZE_MISMATCH;
    }
  }

  /* Verify input file ranges are valid. */
  for (i = 0; i < n_files; ++i) {
    struct stat stat_obj;
    int j;
    if (stat(files[i].filepath, &stat_obj)) {
      return INFILE_ERROR;
    }
    for (j = 0; j < files[i].n_ranges; ++j) {
      if (files[i].ranges[j].start >= stat_obj.st_size) {
        return INVALID_RANGE;
      }
    }
  }

  /* Open infiles */
  for (i = 0; i < n_files; ++i) {
    files[i].fd = fopen(files[i].filepath, "rb");
    if (!files[i].fd) {
      return INFILE_ERROR;
    }
  }

  /* Allocate the buffers */
  buffer_memory = malloc(BUFFER_LENGTH * (n_files + 1));
  if (!buffer_memory) {
    free(buffer_memory);
    return MALLOC_FAILED;
  }

  /* Create outfile */
  outfile->fd = fopen(outfile->filepath, "wb");
  if (!outfile->fd) {
    free(buffer_memory);
    return OUTFILE_ERROR;
  }

  /* Set up the buffer pointers */
  for (i = 0; i < n_files; ++i) {
    files[i].buffer = buffer_memory + BUFFER_LENGTH * i;
  }
  outfile->buffer = buffer_memory + BUFFER_LENGTH * n_files;

  /* All set to do the actual operation. */
  if (total_size > 0) {
    rval = xor_worker(files, n_files, outfile);
  } else {
    rval = SUCCESS;
  }
  
  /* Free all resources */
  free(buffer_memory);
  for (i = 0; i < n_files; ++i) {
    fclose(files[i].fd);
  }
  fclose(outfile->fd);

  return rval;
}

/*
int main(int argc, char** argv) {
*/

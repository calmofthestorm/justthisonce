#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <assert.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/stat.h>

#include "cxor.h"

static inline size_t min(size_t a, size_t b) {
  return a > b ? b : a;
}

size_t get_total_size(const File_t* file) {
  size_t total = 0;
  size_t i;

  for (i = 0; i < file->n_ranges; ++i) {
    total += file->ranges[i].length;
  }
  return total;
}

XorResult xor_worker(File_t inputs[], size_t n_inputs, File_t* output,
                     char* read_buf, char* write_buf) {
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

    remaining = output->range_left;
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

      /* Read in the data we need from all files. Initialize the write buffer
       * with the data from the first file. */
      if (fread(write_buf, 1, len, inputs[0].fd) != len) {
        return INFILE_SEEK_ERROR;
      }
      for (i = 1; i < n_inputs; ++i) {
        if (fread(read_buf, 1, len, inputs[i].fd) != len) {
          return INFILE_SEEK_ERROR;
        } else {
          /* Perform the encryption. Do as much as possible with longs. */
          int j;
          for (j = 0; j < len / sizeof(long); ++j) {
            /* TODO: Consider using intrinsics if the compiler supports them. */
            ((long*)write_buf)[j] ^= ((long*)read_buf)[j];
          }

          /* Finish off any partial words that are not a multiple. */
          for (j = len - (len % sizeof(long)); j < len; ++j) {
            write_buf[j] ^= read_buf[j];
          }
        }
      }

      /* Write to the outfile */
      int i = fwrite(write_buf, 1, len, output->fd);

      /* Keep track of progress */
      assert(len <= remaining);
      remaining -= len;
      for (i = 0; i < n_inputs; ++i) {
        assert(len <= inputs[i].range_left);
        inputs[i].range_left -= len;
      }
      assert(len <= output->range_left);
      output->range_left -= len;
    }
  }
}

XorResult xor_files(File_t files[], const size_t n_files,
                    File_t* outfile) {
  size_t i;

  /* Total size of the range to xor. */
  size_t total_size = get_total_size(outfile);

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
      if (stat_obj.st_size > 0 && files[i].ranges[j].start >= stat_obj.st_size) {
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

  /* Create outfile */
  outfile->fd = fopen(outfile->filepath, "wb");
  if (!outfile->fd) {
    return OUTFILE_ERROR;
  }

  /* All set to do the actual operation. */
  if (total_size > 0) {
    /* Files are read one at a time into here. */
    char* read_buf = malloc(BUFFER_LENGTH);

    /* We accumulate the crypted data here after each read. */
    char* write_buf = malloc(BUFFER_LENGTH);

    if (read_buf && write_buf) {
      rval = xor_worker(files, n_files, outfile, read_buf, write_buf);
    } else {
      rval = MALLOC_FAILED;
    }

    free(read_buf);
    free(write_buf);
  } else {
    rval = SUCCESS;
  }
  
  /* Free all resources */
  for (i = 0; i < n_files; ++i) {
    fclose(files[i].fd);
  }
  fclose(outfile->fd);

  return rval;
}

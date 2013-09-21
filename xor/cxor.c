#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <assert.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/stat.h>

#include "cxor.h"

static int close_file(FILE* file) {
  if (file && file != stdin && file != stdout) {
    return fclose(file);
  } else {
    return 0;
  }
}

int execute_open_input(XorWorkUnit* work, int index, const char* filename) {
  if (work->inputs[index] && work->inputs[index] != stdin &&
      fclose(work->inputs[index])) {
    execute_cleanup(work);
    /* Failed to close old one. */
    return -1;
  }

  if (filename) {
    if (!(work->inputs[index] = fopen(filename, "rb"))) {
      execute_cleanup(work);
      /* Failed to open file. */
      return -1;
    }
  } else if (work->inputs[index ? 0 : 1] != stdin) {
    work->inputs[index] = stdin;
  } else {
    execute_cleanup(work);
    /* Can't have both inputs be stdin. */
    return -1;
  }

  return 0;
}

int execute_open_output(XorWorkUnit* work, const char* filename) {
  if (work->output && work->output != stdout && fclose(work->output)) {
    execute_cleanup(work);
    return -1;
  }

  if (filename) {
    if (!(work->output = fopen(filename, "ab"))) {
      execute_cleanup(work);
      return -1;
    }
  } else {
    work->output = stdout;
  }

  return 0;
}

int execute_seek_input(XorWorkUnit* work, int index, size_t pos) {
  if ((!work->inputs[index] || work->inputs[index] == stdin) || 
      (fseek(work->inputs[index], pos, SEEK_SET))) {
    execute_cleanup(work);
    return -1;
  } else {
    return 0;
  }
}

int execute_xor(XorWorkUnit* work, size_t length) {
  while (length > 0) {
    size_t size = length < BUFFER_LENGTH ? length : BUFFER_LENGTH;
    length -= size;
    if (!work->inputs[0] || !work->inputs[1] || !work->output ||
        fread(work->buf[0], 1, size, work->inputs[0]) != size ||
        fread(work->buf[1], 1, size, work->inputs[1]) != size) {
      execute_cleanup(work);
      return -1;
    }

    /* Perform the encryption. Do as much as possible with machine words.
     * We don't care about endianness because they're read and written in
     * same order. */
    for (int i = 0; i < size / sizeof(size_t); ++i) {
      /* TODO: Consider using intrinsics if the compiler supports them. */
      ((size_t*)work->buf[0])[i] ^= ((size_t*)work->buf[1])[i];
    }

    /* Finish off any partial words that are not a multiple. */
    for (int i = size - (size % sizeof(size_t)); i < size ; ++i) {
      work->buf[0][i] ^= work->buf[1][i];
    }

    if (fwrite(work->buf[0], 1, size, work->output) != size) {
      execute_cleanup(work);
      return -1;
    }
  }

  return 0;
}

int execute_cleanup(XorWorkUnit* work) {
  int success = (close_file(work->inputs[0]) || close_file(work->inputs[1]) ||
                 close_file(work->output));
  work->inputs[0] = work->inputs[1] = work->output = NULL;
  return success;
}

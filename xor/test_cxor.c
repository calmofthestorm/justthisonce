/* Very simple unit tests for the C bindings. More thorough tests of edge cases
 * are tested from the Python tests. */

#include <assert.h>
#define __USE_BSD /* For mkdtemp. */


#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include "cxor.h"

int xor_test(char* inputs[2], size_t length) {
  char tempdir[] = "tmpXXXXXX";
  int rval = 0;
  int i;
  FILE* fd;
  FILE* files[3];
  char fn[3][FILENAME_MAX];

  if (!mkdtemp(tempdir)) {
    fprintf(stderr, "Could not create tempdir.\n");
    return -1;
  }

  for (i = 0; i < 3; ++i) {
    if (snprintf(fn[i], FILENAME_MAX, "%s/file%i", tempdir, i) < 0) {
      fprintf(stderr, "String formatting error.\n");
      return -1;
    }
  }

  for (i = 0; !rval && i < 2; ++i) {
    int n;
    fd = fopen(fn[i], "w");
    if (fd) {
      n = fwrite(inputs[i], 1, length, fd);
      fclose(fd);
    }
    if (!fd || n != length) {
      fprintf(stderr, "File I/O error.\n");
      rval = -1;
    }
  }

  char* buffer = malloc(BUFFER_LENGTH);
  if (!buffer) {
    rval = -1;
    fprintf(stderr, "Malloc failed.\n");
  }

  if (!rval) {
    XorWorkUnit* work = malloc(sizeof(XorWorkUnit));
    if (work) {
      work->output = work->inputs[0] = work->inputs[1] = 0;
    } else {
      fprintf(stderr, "Malloc failed.\n");
      rval = -1;
    }

    for (int i = 0; !rval && i < 2; ++i) {
      if (execute_open_input(work, i, fn[i])) {
        fprintf(stderr, "XOR: Error opening input %i.\n", i);
        rval = -1;
      }
    }

    if (!rval && execute_open_output(work, fn[2])) {
      fprintf(stderr, "XOR: Error opening output.\n");
      rval = -1;
    }

    if (!rval && execute_xor(work, length)) {
      fprintf(stderr, "XOR: Error XORing.\n");
      rval = -1;
    }

    if (!rval && execute_cleanup(work)) {
      fprintf(stderr, "XOR: Error cleaning up.\n");
      rval = -1;
    }

    if (!rval) {
      int n;
      fd = fopen(fn[2], "r");
      if (fd) {
        n = fread(buffer, 1, length, fd);
        fclose(fd);
      }
      if (!fd || n != length) {
        fprintf(stderr, "File I/O error reading output.\n");
        rval = -1;
      } else {
        for (i = 0; !rval && i < length; ++i) {
          int j;
          char c = buffer[i];
          for (j = 0; j < 2; ++j) {
            c ^= inputs[j][i];
          }
          if (c) {
            fprintf(stderr, "Encryption incorrect at offset %i %i\n", i, c);
            rval = -1;
          }
        }
      }
    }
    free(work);
  }

  struct stat st;
  for (i = 0;i < 3; ++i) {
    if (!stat(fn[i], &st)) {
      unlink(fn[i]);
    } 
  }
  rmdir(tempdir);

  free(buffer);
  return rval;
}

int main() {
  char input_buf[2][40] = {"Hello world how are you? I am good!",
                           "Bees!\0Bees!\1BEES!\0Bees!\3Bees!\0Bees!"};
  char* inputs[2] = {input_buf[0], input_buf[1]};
  size_t i;
  for (i = 0; i < 25; ++i) {
    assert(!xor_test(inputs, 35));
  }
  fprintf(stderr, "Test passed!\n");
}

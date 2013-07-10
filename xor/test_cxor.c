/* Very simple unit tests for the C bindings. More thorough tests of edge cases
 * are tested from the Python tests. */
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include "cxor.h"

void test_get_total_size() {
  Range_t ranges[3];
  ranges[0].start = 9;
  ranges[0].length = 7;
  ranges[1].start = 21;
  ranges[1].length = 0;
  ranges[2].start = 100;
  ranges[2].length = 10;
  File_t myfile;
  myfile.n_ranges = 3;
  myfile.ranges = ranges;
  assert(get_total_size(&myfile) == 17);
}

int xor_test_setup_files(char** inputs, size_t input_size, size_t n_inputs,
                         File_t* files, char* buffer) {
  char tempdir[] = "tmpXXXXXX";
  int rval = 0;
  int i;
  FILE* fd;
  if (!mkdtemp(tempdir)) {
    fprintf(stderr, "Could not create tempdir.\n");
    return -1;
  }

  for (i = 0; i < 1 + n_inputs; ++i) {
    if (snprintf(files[i].filepath, FILENAME_MAX, "%s/file%i", tempdir, i) < 0) {
      fprintf(stderr, "String formatting error.\n");
      return -1;
    }
  }

  for (i = 0; !rval && i < n_inputs; ++i) {
    int n;
    fd = fopen(files[i].filepath, "w");
    if (fd) {
      n = fwrite(inputs[i], 1, input_size, fd);
      fclose(fd);
    }
    if (!fd || n != input_size) {
      fprintf(stderr, "File I/O error.\n");
      rval = -1;
    }
  }

  if (!rval) {
    rval = xor_files(files, n_inputs, &files[n_inputs]);
    if (rval) {
      fprintf(stderr, "XOR reports error.\n");
    } else {
      int n;
      fd = fopen(files[n_inputs].filepath, "r");
      if (fd) {
        n = fread(buffer, 1, input_size, fd);
        fclose(fd);
      }
      if (!fd || n != input_size) {
        fprintf(stderr, "File I/O error reading output.\n");
        rval = -1;
      } else {
        for (i = 0; !rval && i < input_size; ++i) {
          int j;
          char c = buffer[i];
          for (j = 0; j < n_inputs; ++j) {
            c ^= inputs[j][i];
          }
          if (c) {
            fprintf(stderr, "Encryption incorrect at offset %i %i\n", i, c);
            rval = -1;
          }
        }
      }
    }
  }

  struct stat st;
  for (i = 0;i < 1 + n_inputs; ++i) {
    if (!stat(files[i].filepath, &st)) {
      unlink(files[i].filepath);
    } 
  }
  rmdir(tempdir);
  return rval;
}

int xor_test(char** inputs, size_t input_size, size_t n_inputs) {
  int i, rval;
  Range_t* ranges = malloc(sizeof(Range_t) * (1 + n_inputs));
  File_t* files = malloc(sizeof(File_t) * (1 + n_inputs));
  char* buffer = malloc(input_size);

  if (ranges && files && buffer) {
    for (i = 0; i < n_inputs + 1; ++i) {
      files[i].n_ranges = 1;
      files[i].ranges = &ranges[i];
      ranges[i].start = 0;
      ranges[i].length = input_size;
    }
    rval = xor_test_setup_files(inputs, input_size, n_inputs, files, buffer);
  } else {
    fprintf(stderr, "Malloc failed.\n");
    rval = -1;
  }

  free(ranges);
  free(files);
  free(buffer);

  return rval;
}

int main() {
  char input_buf[][255] = {"Hello world how are you? I am good!",
                           "World is doing just fine! glad to hear",
                           "Bees!\0Bees!\1BEES!\0Bees!\3Bees!\0Bees!"};
  char* inputs[3] = {input_buf[0], input_buf[1], input_buf[2]};
  int i;
  for (i = 0; i < 25; ++i) {
    assert(!xor_test(inputs, i, 1));
    assert(!xor_test(inputs, i, 2));
    assert(!xor_test(inputs, i, 3));
  }
}

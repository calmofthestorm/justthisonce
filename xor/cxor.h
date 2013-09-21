#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>

#define BUFFER_LENGTH 4 * 1024 * 1024

typedef struct XorWorkUnit {
  FILE* output;
  FILE* inputs[2];
  char buf[2][BUFFER_LENGTH] __attribute__((__aligned__(32)));
} XorWorkUnit;

int execute_xor(XorWorkUnit* work, size_t length);

int execute_open_input(XorWorkUnit* work, int index, const char* filename);

int execute_open_output(XorWorkUnit* work, const char* filename);

int execute_seek_input(XorWorkUnit* work, int index, size_t pos);

int execute_cleanup(XorWorkUnit* work);

/* REQUIRES: Open files for inputs and output, and two valid buffers of the
 *           given length. All inputs valid.
 *
 * MODIFIES: input_files position, output file's contents, and the buffers.
 *
 * EFFECTS:  Files xored.*/
int xor_files(FILE* input_files[2], char* buf[2], FILE* output_file,
              size_t length);

/* REQUIRES: src and dest are valid buffers of at least given length.
 * EFFECTS:  dest contains src ^ dest for length*/
void xor_buffers(char* dest, const char* src, int length);

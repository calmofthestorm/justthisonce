#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>

/* Read and write in multiples of this amount. C90 forbids the use of variables
 * (even consts) as lengths lengths for stack-allocated arrays. */
#define BUFFER_LENGTH 4 * 1024 * 1024

typedef enum {SUCCESS=0, NO_WORK=1, SIZE_MISMATCH=2, OUTFILE_ERROR=3,
              INFILE_ERROR=4, MALLOC_FAILED=5, INVALID_RANGE=6,
              INFILE_SEEK_ERROR=-1, OUTFILE_SEEK_ERROR=-2} XorResult;

/* Structure to represent a single range in a single file to xor. */
typedef struct {
  size_t start;
  size_t length;
} Range_t;

/* Structure to represent ranges in a file. It is acceptable for ranges
   to overlap because checking for this in C is complex. */
typedef struct {
  size_t n_ranges;
  char filepath[FILENAME_MAX];
  Range_t* ranges;
  /* used internally */
  FILE* fd;
  size_t size;
  size_t range_left; /* Number of bytes in current range left */
  size_t cur_range;  /* Index of current range */
} File_t;

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
                    File_t* outfile);

/* EFFECTS: Returns the min of a and b. */
static inline size_t min(size_t a, size_t b);

/* REQUIRES: file points to a valid file structure.
   RETURNS:  the total size of all ranges in the file. Overlapping segments
             are counted multiple times. */
size_t get_total_size(const File_t* file);

/* REQUIRES: all file objects completely valid.
   MODIFIES: the buffers and files open by the fds in the file objects
   RETURNS:  SUCCESS (0) */
XorResult xor_worker(File_t inputs[], size_t n_inputs, File_t* output,
                     char* read_buf, char* write_buf);

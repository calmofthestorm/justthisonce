#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <assert.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <immintrin.h>

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

static void xor_c  (char *out, const char *pad, size_t size) {
    typedef size_t chunk_t;

    size_t i;
    size_t integral_size = size & ~(sizeof(chunk_t) - 1u);
    /* Do as much as possible with machine words. */
    for (i = 0; i < integral_size; i += sizeof(chunk_t)) {
        *(chunk_t *) (out + i) ^= *(const chunk_t *) (pad + i);
    }

    /* Finish off partial words. */
    for (; i < size; i++) {
        out[i] ^= pad[i];
    }
}

#ifdef __SSE__
static void xor_sse(char *out, const char *pad, size_t size) {
    size_t i;
    size_t integral_size = size & ~(15u);
    for (i = 0; i < integral_size; i += 16u) {
        /*
         * Until we can guarantee that the buffers are properly (16-byte)
         * aligned, we use the unaligned forms.
         */
        __m128 o = _mm_loadu_ps((const float *) (out + i));
        __m128 p = _mm_loadu_ps((const float *) (pad + i));

        _mm_storeu_ps((float *) (out + i), _mm_xor_ps(o, p));
    }

    /* Finish off partial words. */
    for (; i < size; i++) {
        out[i] ^= pad[i];
    }
}
#endif

#ifdef __AVX__
static void xor_avx(char *out, const char *pad, size_t size) {
    size_t i;
    size_t integral_size = size & ~(31u);
    for (i = 0; i < integral_size; i += 32u) {
        /*
         * Until we can guarantee that the buffers are properly (32-byte)
         * aligned, we use the unaligned forms.
         */
        __m256 o = _mm256_loadu_ps((const float *) (out + i));
        __m256 p = _mm256_loadu_ps((const float *) (pad + i));

        _mm256_storeu_ps((float *) (out + i), _mm256_xor_ps(o, p));
    }

    /* Finish off partial words. */
    for (; i < size; i++) {
        out[i] ^= pad[i];
    }
}
#endif

typedef void (*xor_f)(char *, const char *, size_t);
static xor_f f =
#if defined(__SSE__) || defined(__AVX__)
    /* We have something to check at runtime. */
    NULL
#else
    /* Use the C-based codepath, as neither SSE nor AVX have compiler support */
    xor_c
#endif
    ;

/**
 * This is a no-op if f.  Otherwise, we use cpuid to identify the available
 * codepaths available to us.  As we expect these instruction sets to remain
 * constrant throughout execution, this function should produce the same results
 * and consequently, it is safe to call concurrently (so long as f has a memory
 * type that supports atomic stores in light of parallel writers).
 */
static void select_xor() {
    if (f) {
        return;
    }

    #if __x86_64__ || __i386__
    unsigned flags_a, flags_b, flags_c, flags_d;

    __asm__("cpuid" :
        "=a"(flags_a), "=b"(flags_b), "=c"(flags_c), "=d"(flags_d) : "a"(1));

    #ifdef __AVX__
    const unsigned avx_osxsave = 0x18000000;

    if ((flags_c & avx_osxsave) == avx_osxsave) {
        unsigned eax, edx;
        __asm__("xgetbv" : "=a"(eax), "=d"(edx) : "c"(0));
        if ((eax & 0x06) == 0x06) {
            f = xor_avx;
            return;
        }
    }
    #endif

    #ifdef __SSE__
    const unsigned sse = 0x01000000;

    if ((flags_d & sse) == sse) {
        f = xor_sse;
        return;
    }
    #endif
    #endif

    f = xor_c;
}

int execute_xor(XorWorkUnit* work, size_t length) {
  /* Choose the xor algorithm. */
  select_xor();

  while (length > 0) {
    size_t size = length < BUFFER_LENGTH ? length : BUFFER_LENGTH;
    length -= size;
    if (!work->inputs[0] || !work->inputs[1] || !work->output ||
        fread(work->buf[0], 1, size, work->inputs[0]) != size ||
        fread(work->buf[1], 1, size, work->inputs[1]) != size) {
      execute_cleanup(work);
      return -1;
    }

    /* Perform the encryption. */
    f(work->buf[0], work->buf[1], size);

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

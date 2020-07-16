// Copyright 2020 truher
// Base85 encoder

#include "b85.h"

uint32_t encode_85(const unsigned char* in, uint32_t len, char* out) {
  char* out_start = out;
  while (len) {
    uint32_t in_chunk = 0;
    for (int8_t cnt = 24; cnt >= 0; cnt -= 8) {
      in_chunk |= *in++ << cnt;
      if (--len == 0)
        break;
    }
    for (int8_t out_offset = 4; out_offset >= 0; out_offset--) {
      out[out_offset] = alphabet[in_chunk % 85];
      in_chunk /= 85;
    }
    out += 5;
  }
  *out = 0;
  return out - out_start;
}

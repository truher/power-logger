// Copyright 2020 truher
// Base85 encoder

#ifndef ARDUINO_B85_H_
#define ARDUINO_B85_H_

#include <stdint.h>

static const char alphabet[] = {
  '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
  'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
  'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T',
  'U', 'V', 'W', 'X', 'Y', 'Z',
  'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j',
  'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
  'u', 'v', 'w', 'x', 'y', 'z',
  '!', '#', '$', '%', '&', '(', ')', '*', '+', '-',
  ';', '<', '=', '>', '?', '@', '^', '_', '`', '{',
  '|', '}', '~'
};

// returns the size of the encoded buffer, not including the terminating null
uint32_t encode_85(const unsigned char* in, uint32_t len, char* out);

#endif  // ARDUINO_B85_H_

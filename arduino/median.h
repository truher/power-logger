// Copyright 2020 truher
// Quickselect median

#ifndef ARDUINO_MEDIAN_H_
#define ARDUINO_MEDIAN_H_

#include <stdint.h>
#include <algorithm>
#include <iterator>

template <typename T>
T median(T* data, uint16_t len) {
  uint16_t kth = len & 1 ? len / 2 : (len / 2) - 1;
  std::nth_element(data, data + kth, data + len);
  return data[kth];
}

#endif  // ARDUINO_MEDIAN_H_

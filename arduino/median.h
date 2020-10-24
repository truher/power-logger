// Copyright 2020 truher
// Quickselect median

#ifndef ARDUINO_MEDIAN_H_
#define ARDUINO_MEDIAN_H_

#include <stdint.h>

template <typename T>
T median(T* data, uint16_t len) {
  int kth = len & 1 ? len / 2 : (len / 2) - 1;
  int i, j, left, right;
  left = 0;
  right = len - 1;
  while (left < right) {
    i = left;
    j = right;
    do {
      while (data[i] < data[kth]) i++;
      while (data[kth] < data[j]) j--;
      if (i <= j) {
        std::swap(data[j], data[i]);
        i++;
        j--;
      }
    } while (i <= j);
    if (j < kth) left = i;
    if (kth < i) right = j;
  }
  return data[kth];
  
}

#endif  // ARDUINO_MEDIAN_H_

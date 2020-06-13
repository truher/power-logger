// Copyright 2020 Truher
#include <avr/boot.h>

enum Column {
  VOLTS, AMPS
};
Column column = VOLTS;

char uidStr[19] = {0};
const unsigned int ROWS = 1000;
const unsigned int LED_EMON = 9;

// observations from analogRead()
uint8_t volts[ROWS];
uint8_t amps[ROWS];

// which observation we're making, also the read/print semaphore
int row = 0;

// ct sensor in [1..4] (leonardo) or [2..15] (mega)
const int MIN_CT = 2;
const int MAX_CT = 15;
int ct = MIN_CT;

// for delta encoding
int v_first = 0;
int a_first = 0;
int v_prev = 0;
int a_prev = 0;

// for overflows in delta
bool err = false;

void setup() {
  snprintf(uidStr, sizeof(uidStr), "%02X%02X%02X%02X%02X%02X%02X%02X%02X",
    boot_signature_byte_get(14), boot_signature_byte_get(15),
    boot_signature_byte_get(16), boot_signature_byte_get(17),
    boot_signature_byte_get(18), boot_signature_byte_get(19),
    boot_signature_byte_get(21), boot_signature_byte_get(22),
    boot_signature_byte_get(23));
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(LED_EMON, OUTPUT);

  // set up Serial
  Serial.begin(115200);
  while (!Serial) {}

  // Set up ADC
  // Clear prescale
  ADCSRA &= ~(bit(ADPS0) | bit(ADPS1) | bit(ADPS2));
  // ADC prescale = 32, tradeoff between duration and accuracy
  ADCSRA |= bit(ADPS0) | bit(ADPS2);
  analogRead(0);

  // initialize timer1
  noInterrupts();
  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1  = 0;
  // Set compare match register
  // OCR1A = 800;  // 16MHz/1prescale/10khz/2 samples (50us) = 6 cycles per measurement
  OCR1A = 1600;  // 16MHz/1prescale/5khz/2 samples (100us) = 12 cycles per measurement
  TCCR1B |= (1 << WGM12);  // CTC mode
  TCCR1B |= (1 << CS10);  // prescale = 1
  TIMSK1 |= (1 << OCIE1A);  // enable timer compare interrupt
  interrupts();
}
int v = 0;
int a = 0;
int vv = 0;
int aa = 0;

ISR(TIMER1_COMPA_vect) {
  if (row >= ROWS) return;  // wait for printing to be done

  // TODO(truher): remove the duplication here
  switch (column) {
    case VOLTS:
      // TODO: fix this for the mega case, 120/240 etc
      v = analogRead(0);
      if (row == 0) {
        v_first = v;
        volts[0] = 128;
      } else {
        vv = v - v_prev + 128;
        if (vv > 255 || vv < 0) {
          err = true;
          volts[row] = 128;
        } else {
          volts[row] = (uint8_t) vv;
        }
      }
      v_prev = v;
      column = AMPS;
      break;
    case AMPS:
      a = analogRead(ct);
      if (row == 0) {
        a_first = a;
        amps[0] = 128;
      } else {
        aa = a - a_prev + 128;
        if (aa > 255 || aa < 0) {
          err = true;
          amps[row] = 128;
        } else {
          amps[row] = (uint8_t) aa;
        }
      }
      a_prev = a;
      column = VOLTS;
      ++row;
      break;
  }

  if (row >= ROWS)
    TCCR1B = 0;  // stop timer
}

char big_buf[65];  // usb packets are 64 (32u4 default fifo)

void serialize(uint8_t* samples) {
  // half the bytes == zero-overhead encoding experiment
  // TODO: remove this
  // for (int r = 0; r < 500; r += 20) {
  // TODO: ten samples is just about the same as 20, do that instead?
  // TODO: cobs encoding, half the bytes :-)
  for (int r = 0; r < ROWS; r += 20) {
    snprintf(big_buf, sizeof(big_buf),
    "%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X",
      samples[r+0], samples[r+1], samples[r+2], samples[r+3], samples[r+4],
      samples[r+5], samples[r+6], samples[r+7], samples[r+8], samples[r+9],
      samples[r+10], samples[r+11], samples[r+12], samples[r+13], samples[r+14],
      samples[r+15], samples[r+16], samples[r+17], samples[r+18], samples[r+19]);
    for (int z = 0; z < 20; ++z) {
      samples[r+z] = 0;
    }
    Serial.write(big_buf, 40);
  }
}

void loop() {
  if (row < ROWS) return;  // wait for measurement to be done
  digitalWrite(LED_EMON, LOW);

  digitalWrite(LED_BUILTIN, digitalRead(LED_BUILTIN) ^ 1);

  snprintf(big_buf, sizeof(big_buf), "%d\t%s\tct%d\t%d\t",err,uidStr,ct,v_first);
  Serial.print(big_buf);
  serialize(volts);
  snprintf(big_buf, sizeof(big_buf), "\t%d\t", a_first);
  Serial.print(big_buf);
  serialize(amps);
  Serial.println();

  // restart measurement
  err = false;
  ++ct;
  if (ct > MAX_CT) ct = MIN_CT;
  row = 0;
  digitalWrite(LED_EMON, HIGH);
  TCCR1B |= (1 << WGM12);
  TCCR1B |= (1 << CS10);
}

// Copyright 2020 Truher
#include <avr/boot.h>

enum Column {
  VOLTS, AMPS
};
Column column = VOLTS;

char uidStr[19] = {0};
const unsigned int ROWS = 1000;

// observations from analogRead()
uint8_t volts[ROWS];
uint8_t amps[ROWS];

// which observation we're making, also the read/print semaphore
int row = 0;

// ct sensor in [1,2,3,4]
int ct = 1;

char buf[3];  // for each observation byte

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
  // OCR1A = 800;  // 16MHz/1/10khz/2 samples (50us) = 6 cycles per measurement
  OCR1A = 1600;  // 16MHz/1/5khz/2 samples (100us) = 12 cycles per measurement
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

void loop() {
  if (row < ROWS) return;  // wait for measurement to be done

  digitalWrite(LED_BUILTIN, digitalRead(LED_BUILTIN) ^ 1);

  // TODO(truher): extract a serialize function, test it.
  Serial.print(err);
  Serial.print("\t");
  Serial.print(uidStr);
  Serial.print("\tct");
  Serial.print(ct);
  Serial.print("\t");
  Serial.print(v_first);
  Serial.print("\t");
  for (int r = 0; r < ROWS; ++r) {
    snprintf(buf, sizeof(buf), "%02X", volts[r]);
    volts[r] = 0;
    Serial.write(buf, 2);
  }
  Serial.print("\t");
  Serial.print(a_first);
  Serial.print("\t");
  for (int r = 0; r < ROWS; ++r) {
    snprintf(buf, sizeof(buf), "%02X", amps[r]);
    amps[r] = 0;
    Serial.write(buf, 2);
  }
  Serial.println();

  // restart measurement
  err = false;
  ++ct;
  if (ct > 4) ct = 1;
  row = 0;
  TCCR1B |= (1 << WGM12);
  TCCR1B |= (1 << CS10);
}

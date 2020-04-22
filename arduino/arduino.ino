#include <avr/boot.h>

char uidStr[20] = {0};

void initUID() {
  uint8_t UID[9];
  for (size_t i = 0; i < 9; i++) {
    UID[i] = boot_signature_byte_get(0x0E + i + (i > 5 ? 1 : 0));
  }
  sprintf(uidStr,"%02X%02X%02X%02X%02X%02X%02X%02X%02X",
          UID[0],UID[1],UID[2],UID[3],UID[4],UID[5],UID[6],UID[7],UID[8]);
}

void printVI(const uint8_t inPinV, const uint8_t inPinI) {
  Serial.print(" ");
  Serial.print(inPinI);
  Serial.print(" ");
  for (int i =0; i < 100; i++) {
    Serial.print(analogRead(inPinV));
    Serial.print(" ");
    Serial.print(analogRead(inPinI));
    Serial.print(" ");
  }
  Serial.println();
}

void setup() {
  initUID(); 
  Serial.begin(115200);
  while (!Serial) {}
  
  const int LEDpin = 9;
  pinMode(LEDpin, OUTPUT);                                              
  digitalWrite(LEDpin, HIGH);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  Serial.println();
  Serial.println();
  Serial.println();
}

void loop() {
  digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));  // toggle the light once per loop
  Serial.print(uidStr);
  printVI(0, 1);
  printVI(0, 2);
  printVI(0, 3);
  printVI(0, 4);

  delay(1000);
}

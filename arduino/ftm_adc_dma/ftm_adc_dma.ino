// see EEOL_2014APR24_AMP_CTRL_AN_01.pdf
// see ADC_Module.cpp


const uint8_t pinLED = 13; // built-in LED
uint8_t LED_ON = true;
uint32_t iCounter = 0;

void setup() {
  Serial.begin(0);
  //while (!Serial);  // this makes it hang until serial monitor is opened.  :-(
  pinMode(pinLED, OUTPUT);

  FTM0_POL = 0;
  FTM0_OUTMASK = 0xFF; // mask all
  FTM0_SC = 0x00; // reset status == turn off FTM
  FTM0_CNT = 0x00;  // zero the counter, or maybe this does nothing
  FTM0_CNTIN = 0; // counter initial value
  FTM0_C0SC = FTM_CSC_ELSB | FTM_CSC_MSB; // output compare, high-true
  FTM0_MOD = 32;  // modulo, for the counter, output high on overflow
  FTM0_C0V = 16;  // match value, output low on match

  // bga pin b11 is port c1, which is pin 22 or a8
  CORE_PIN22_CONFIG = PORT_PCR_MUX(4) // in alternative 4, ftm0_ch0 goes to b11
                    | PORT_PCR_DSE    // high drive strength
                    | PORT_PCR_SRE;   // slow slew rate (?)

  NVIC_SET_PRIORITY(IRQ_FTM0, 64);  // 0?  64?  who knows?
  NVIC_ENABLE_IRQ(IRQ_FTM0);
  
  FTM0_SC = FTM_SC_CLKS(1)   // set status: system clock
            | FTM_SC_PS(0)   // no prescaling
            | FTM_SC_TOIE;   // enable overflow interrupts

  FTM0_OUTMASK = 0xFE; // enable only FTM0_CH0

}


void loop()
{
  // empty
}


void ftm0_isr(void) {
  FTM0_SC &= ~FTM_SC_TOF; // clear the interrupt overflow flag
  iCounter ++; // time base counter
  if (iCounter >= 100000) { // 1 second
    iCounter = 0;
    Serial.println(">");
    if (LED_ON == true) {
      digitalWriteFast(pinLED, HIGH);
    }
    else {
      digitalWriteFast(pinLED, LOW);
    }
    LED_ON = !LED_ON;
  }
}

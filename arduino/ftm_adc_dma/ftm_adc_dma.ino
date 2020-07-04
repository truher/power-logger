//

// see EEOL_2014APR24_AMP_CTRL_AN_01.pdf
// see ADC_Module.cpp


const uint8_t pinLED = 13; // built-in LED
uint8_t LED_ON = true;
uint32_t iCounter = 0;

volatile unsigned short result0RA;
volatile unsigned short result1RA;

void toggleLED() {
    if (LED_ON == true) {
      digitalWriteFast(pinLED, HIGH);
    }
    else {
      digitalWriteFast(pinLED, LOW);
    }
    LED_ON = !LED_ON;
}

void ftm0_isr(void) {
//void foooo(void) { 
  FTM0_SC &= ~FTM_SC_TOF; // clear the interrupt overflow flag
  iCounter ++; // time base counter
  if (iCounter >= 100000) { // 1 second
    iCounter = 0;

    Serial.print(result0RA);
    Serial.print(", ");
    Serial.print(result1RA);
    Serial.println();

 //toggleLED();
  }
}

// just try the other name, which is auto registered
//void ADC0_IRQHandler(void) { 
void adc0_isr() {
  if ( ADC0_SC1A & ADC_SC1_COCO )
    result0RA = (unsigned short) ADC0_RA;
 // if ( ADC1_SC1A & ADC_SC1_COCO )
 //   result1RA = (unsigned short) ADC1_RA;
   if ( ADC1_SC1A & ADC_SC1_COCO )
    result1RA = (unsigned short) ADC1_RA;

 toggleLED();
}

////void ADC1_IRQHandler(void) {
//void adc1_isr() {
//
//  if ( ADC1_SC1A & ADC_SC1_COCO )
//    result1RA = (unsigned short) ADC1_RA;
//  toggleLED();
//}


void setup() {
  Serial.begin(0);
  while (!Serial);  // this makes it hang until serial monitor is opened.  :-(
  pinMode(pinLED, OUTPUT);

  // FTM INITIALIZATION
  
  FTM0_POL = 0;
  FTM0_OUTMASK = 0xFF; // mask all
  FTM0_SC = 0x00; // reset status == turn off FTM
  FTM0_CNT = 0x00;  // zero the counter, or maybe this does nothing
  FTM0_CNTIN = 0; // counter initial value
  FTM0_C0SC = FTM_CSC_ELSB | FTM_CSC_MSB; // output compare, high-true
  FTM0_MOD = 32;  // modulo, for the counter, output high on overflow
  FTM0_C0V = 16;  // match value, output low on match

  // bga pin b11 (row b, column 11) is port c1 ("PTC1"), which is teensy pin 22 or a8
  // CORE_PIN22_CONFIG ... do i need that alias?
  PORTC_PCR1 = PORT_PCR_MUX(4) // in alternative 4, ftm0_ch0 goes to b11
             | PORT_PCR_DSE    // high drive strength
             | PORT_PCR_SRE;   // slow slew rate (?)

  NVIC_SET_PRIORITY(IRQ_FTM0, 64);  // 0?  64?  who knows?
  NVIC_ENABLE_IRQ(IRQ_FTM0);
  
  FTM0_SC = FTM_SC_CLKS(1)   // set status: system clock
            | FTM_SC_PS(0)   // no prescaling
            | FTM_SC_TOIE;   // enable overflow interrupts

  FTM0_EXTTRIG |= FTM_EXTTRIG_INITTRIGEN;  // FTM output trigger enable
  FTM0_MODE |= FTM_MODE_INIT;  // initialize the output

  FTM0_OUTMASK = 0xFE; // enable only FTM0_CH0

  // ADC INITIALIZATION

  SIM_SOPT7 = SIM_SOPT7_ADC0ALTTRGEN  // enable alternate trigger
            | SIM_SOPT7_ADC1ALTTRGEN
            | SIM_SOPT7_ADC0TRGSEL(8) // select FTM0 trigger
            | SIM_SOPT7_ADC1TRGSEL(8);

  ADC0_CFG1 |= ADC_CFG1_MODE(3);  // 16 bit
  ADC1_CFG1 |= ADC_CFG1_MODE(3);

  ADC0_CFG2 |= ADC_CFG2_ADHSC   // high speed
            |  ADC_CFG2_MUXSEL; // select "b" channels
  ADC1_CFG2 |= ADC_CFG2_ADHSC;

  ADC0_SC2 |= ADC_SC2_ADTRG;  // hardware trigger, TODO also DMAEN dma enable
  ADC1_SC2 |= ADC_SC2_ADTRG;

  ADC0_SC1A = ADC_SC1_AIEN     // interrupt enable, TODO differential
            | ADC_SC1_ADCH(5); // ADC0_SE5b, PTD1, D4, teensy "A0"
  ADC1_SC1A = ADC_SC1_AIEN
            | ADC_SC1_ADCH(8); // ADCx_SE8, PTB0, H10, teensy "A2"

  SIM_SCGC6 |= SIM_SCGC6_FTM0  // ftm0 clock gate
            |  SIM_SCGC6_ADC0; // adc0 clock gate
  SIM_SCGC3 |= SIM_SCGC3_ADC1; // adc1 clock gate

  // TODO: these interrupts will interrupt each other needlessly?
  //attachInterruptVector(IRQ_ADC0, &ADC0_IRQHandler);
  //attachInterruptVector(IRQ_ADC1, &ADC1_IRQHandler);
 // attachInterruptVector(IRQ_FTM0, foooo);
  NVIC_SET_PRIORITY(IRQ_ADC0, 64);  // 0?  64?  who knows?
 // NVIC_SET_PRIORITY(IRQ_ADC1, 65);  // 0?  64?  who knows?
  NVIC_ENABLE_IRQ(IRQ_ADC0);
 // NVIC_ENABLE_IRQ(IRQ_ADC1);
}










void loop()
{
  // empty
}

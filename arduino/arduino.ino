// Copyright 2020 truher
// Teensy 3.5 two-channel synchronized ADC
#include <stdint.h>
#include "b85.h"
#include "median.h"
#include <numeric>

struct adcx {
  uint8_t ch;
  uint8_t muxsel;
};

struct ct {
  adcx adc0;  // volts but note 240v is reversed since adc1
  adcx adc1;  // amps
} cts[] = {
  // this is in order on the board
  // 240v ADC1_DP0 "A12" and ADC1_DM0 "A11"  ADC1 is volts, differential, always 0
  {{ 4, 1}, { 0, 0}},  // ADC0_SE4b  "A9"
  {{ 6, 1}, { 0, 0}},  // ADC0_SE6b  "A6"
  {{12, 0}, { 0, 0}},  // ADC0_SE12  "A5"
  {{13, 0}, { 0, 0}},  // ADC0_SE13  "A4"
  {{ 9, 0}, { 0, 0}},  // ADC0_SE9   "A3"
  {{ 8, 0}, { 0, 0}},  // ADC0_SE17  "A2"
  {{14, 0}, { 0, 0}},  // ADC0_SE14  "A1"
  {{ 5, 1}, { 0, 0}},  // ADC0_SE5b  "A0"
  // 120v L1 ADC0_SE7b "A7"  ADC0 is volts
  {{ 7, 1}, {23, 0}},  // ADC1_SE23  "A22"
  {{ 7, 1}, {17, 0}},  // ADC1_SE17  "A20"
  {{ 7, 1}, { 7, 1}},  // ADC1_SE7b  "A19"
  {{ 7, 1}, { 6, 1}},  // ADC1_SE6b  "A18"
  // 120v L2 ADC0_SE15 "A8"  ADC0 is volts
  {{15, 0}, { 5, 1}},  // ADC1_SE5b  "A17"
  {{15, 0}, { 4, 1}},  // ADC1_SE4b  "A16"
  {{15, 0}, {15, 0}},  // ADC1_SE15  "A13"
  {{15, 0}, {14, 0}},  // ADC1_SE14  "A12"

  //  {{ 7, 1}, {14, 0}},  // ADC1_SE14  "A12"
  //  {{ 7, 1}, {15, 0}},  // ADC1_SE15  "A13"
  //  {{ 7, 1}, { 4, 1}},  // ADC1_SE4b  "A16"
  //  {{15, 0}, { 6, 1}},  // ADC1_SE6b  "A18"
  //  {{15, 0}, { 7, 1}},  // ADC1_SE7b  "A19"
  //  {{15, 0}, {17, 0}},  // ADC1_SE17  "A20"
};

uint8_t current_ct = 0;

char uidStr[17] = {0};  // the lower 2 bytes of the UID

static const uint8_t pinLED = 13;
static const uint8_t PIN_ADC_COCO = 25;

// 32767 but ideally divisible by 4 for b85... is that actually necessary?
// const uint32_t MAX_BUFFER_SIZE = 1600;
// in samples, which is 16b not 8b
//static const uint32_t MAX_BUFFER_SIZE = 1000;  // TODO: harmonize this with L below
//static const uint32_t MAX_BUFFER_SIZE = 10000;  // TODO: harmonize this with L below
static const uint32_t MAX_BUFFER_SIZE = 20000;  // TODO: harmonize this with L below

// TODO: clean up the actual vs reported sample rate etc, make stride adjustable.
uint16_t decimation_stride = 10;
//uint16_t decimation_stride = 20;
//uint16_t decimation_stride = 5;


//uint16_t current_length = 1000;
uint16_t current_length = 10000;
//uint16_t current_length = 20000;
//uint32_t current_frequency = 5000;  // in hz
uint32_t current_frequency = 50000;  // in hz
//uint32_t current_frequency = 100000;  // in hz
//uint32_t current_frequency = 25000;  // in hz
uint32_t current_channel = 0;       // zero means "scan all"
//uint16_t new_length = 1000;         // for next round
//uint32_t new_frequency = 5000;      // in hz, for next round
uint16_t new_length = 10000;         // for next round
uint32_t new_frequency = 50000;      // in hz, for next round
uint32_t new_channel = 0;
//DMAMEM static volatile uint16_t __attribute__((aligned(32))) buffer0[MAX_BUFFER_SIZE];
//DMAMEM static volatile uint16_t __attribute__((aligned(32))) buffer1[MAX_BUFFER_SIZE];
//volatile uint16_t buffer0_filtered[MAX_BUFFER_SIZE];
//volatile uint16_t buffer1_filtered[MAX_BUFFER_SIZE];
// try signed
DMAMEM static volatile int16_t __attribute__((aligned(32))) buffer0[MAX_BUFFER_SIZE];
DMAMEM static volatile int16_t __attribute__((aligned(32))) buffer1[MAX_BUFFER_SIZE];
volatile int16_t buffer0_filtered[MAX_BUFFER_SIZE];
volatile int16_t buffer1_filtered[MAX_BUFFER_SIZE];

// 2 for sample width, 5/4 for b85, 1 for /0
static const uint32_t MAX_ENCODED_BUFFER_SIZE =
  static_cast<int>(MAX_BUFFER_SIZE * 2 * 5 / 4) + 1;
char encoded_buf[MAX_ENCODED_BUFFER_SIZE];

void restartTimer() {
  // the new_* values can be set anytime;
  // pick them up here.
  current_length = new_length;
  set_length(current_length);
  current_frequency = new_frequency;
  set_frequency(current_frequency);

  // the ct can only be set here.
  current_ct += 1;
  if (current_ct > 15) current_ct = 0;
  set_ct(current_ct);

  DMA_SERQ = 0;  // enable DMA channel 0
  DMA_SERQ = 1;  // enable DMA channel 1
  // turn the timer back on
  FTM1_SC = (FTM1_SC & ~FTM_SC_CLKS_MASK) | FTM_SC_CLKS(1);
}

uint32_t encoded_len = 0;

template <typename T>
int filter(T* in, int in_len, int stride, T* out) {
  int out_len = 0;
  for (int i = 0; i + stride - 1 < in_len; i += stride) {
    out[out_len] = median<T>(in + i, stride);
    ++out_len;
  }
  return out_len;
}

void WriteOutput() {

//  int outlen0 = filter<volatile uint16_t>(buffer0, current_length, decimation_stride, buffer0_filtered);
//  filter<volatile uint16_t>(buffer1, current_length, decimation_stride, buffer1_filtered);
//  int outlen0 = filter<volatile int16_t>((volatile int16_t*)buffer0, current_length, decimation_stride, (volatile int16_t*)buffer0_filtered);
//  filter<volatile int16_t>((volatile int16_t*)buffer1, current_length, decimation_stride, (volatile int16_t*)buffer1_filtered);
// try signed
  int outlen0 = filter<volatile int16_t>(buffer0, current_length, decimation_stride, buffer0_filtered);
  filter<volatile int16_t>(buffer1, current_length, decimation_stride, buffer1_filtered);
  
  ct the_ct = cts[current_ct];
  bool v1 = the_ct.adc1.ch == 0;  // ch0 means volts is adc1 so dma1 so buffer1
  Serial.print(uidStr);
  Serial.print("\tct");
  Serial.print(current_ct);         // TODO(truher): real ct channels and names
  Serial.print("\t");
  //Serial.print(current_frequency);
  Serial.print(current_frequency/decimation_stride);
  Serial.print("\t");
  Serial.print(outlen0);
  //  Serial.print(current_length);
  Serial.print("\t");

  // flip buffer 0 and buffer 1 so that volts are always first.
  // TODO: do this more cleanly
  encoded_len = encode_85((const unsigned char *)((v1 ? buffer1_filtered : buffer0_filtered)), outlen0 * 2, encoded_buf);
  Serial.write(encoded_buf, encoded_len);  // this is volts
  Serial.print("\t");
  encoded_len = encode_85((const unsigned char *)((v1 ? buffer0_filtered : buffer1_filtered)), outlen0 * 2, encoded_buf);
  Serial.write(encoded_buf, encoded_len);  // this is amps
  Serial.println();
  Serial.send_now();
}

// if neither channel is done, we shouldn't be here.
// if one channel is done, let the other finish, it won't hurt anything.
// if both channels are done, then set up a new run.
void maybeRestart() {
  if (DMA_ERQ & DMA_ERQ_ERQ0) return;  // channel 0 still enabled
  if (DMA_ERQ & DMA_ERQ_ERQ1) return;  // channel 1 still enabled

  // turn off the timer
  FTM1_SC = (FTM1_SC & ~FTM_SC_CLKS_MASK) | FTM_SC_CLKS(0);

  digitalWriteFast(pinLED, HIGH);

  WriteOutput();

  // TODO(truher): reconfigure ADC channels etc

  digitalWriteFast(pinLED, LOW);

  restartTimer();
}

// interrupt on DMA 0 buffer full
void dma_ch0_isr() {
  DMA_CINT = DMA_CINT_CINT(0);  // clear the interrupt to avoid infinite loop
  maybeRestart();
}

// interrupt on DMA 1 buffer full
void dma_ch1_isr() {
  DMA_CINT = DMA_CINT_CINT(1);
  maybeRestart();
}

// interrupt on conversion complete
void adc0_isr() {
//  // int result = ADC0_RA; // TODO REMOVE
//  digitalWriteFast(PIN_ADC_COCO, HIGH);
//  delayMicroseconds(1);
//  digitalWriteFast(PIN_ADC_COCO, LOW);//
}

void adc1_isr() {
//  // int result = ADC1_RA;  // TODO REMOVE/
}

void set_length(uint16_t len) {
  // major loop size is buffer size (max 32k)
  DMA_TCD0_CITER_ELINKNO = len;
  DMA_TCD1_CITER_ELINKNO = len;
  DMA_TCD0_BITER_ELINKNO = len;
  DMA_TCD1_BITER_ELINKNO = len;

  // after major loop, go back to the start
  DMA_TCD0_DLASTSGA = -2 * len;  // promoted to int32_t
  DMA_TCD1_DLASTSGA = -2 * len;
}

// TODO(truher): higher frequencies seem to corrupt the output.
// TODO(truher): calibrate the actual frequency with the scope
void set_frequency(uint32_t freq) {
  // the slowest possible is the highest possible mod (65535) of the highest
  // possible prescale (128), of the 60mhz clock, so that's about
  // 7 hz.

  uint32_t new_mod = (F_BUS / freq);

  uint32_t new_half_mod = static_cast<uint32_t> (new_mod / 2);
// ??? TODO ... this is the wrong frequency? no.
//  uint32_t new_half_mod = static_cast<uint32_t> (new_mod / 3);

  new_mod &= 0xFFFF;
  new_half_mod &= 0xFFFF;
  // modulo, for the counter, output high on overflow
  FTM1_MOD = new_mod;

  // match value, output low on match
  FTM1_C0V = new_half_mod;

  FTM1_SC = FTM_SC_CLKS(1)   // system clock
            | FTM_SC_PS(0);  // no prescaling
  //        | FTM_SC_TOIE;   // enable overflow interrupts
}

void calibrate_adc() {
  /*
    analog_init is called in pins_teensy.c, with some defaults.
    TODO: calibrate the vref trim
    VREF_TRM => chop enable (required).  trim level is set to the middle.
    VREF_SC  => enable vref, regulator, compensation (all required), 'high power mode'
    ADCx_CFG1 (fixed)
    ADCx_CFG2 (fixed)
    ADCx_SC2  (fixed)
    ADCx_SC3  (fixed)
    also the calibration is done wrong, so do it over again.
  */
  __disable_irq();
  ADC0_SC3 = 0;   // stop any current calibration
  ADC1_SC3 = 0;
  ADC0_SC3 = ADC_SC3_CALF;  // clear failure
  ADC1_SC3 = ADC_SC3_CALF;
  ADC0_SC3 = ADC_SC3_CAL;  // start calibration
  ADC1_SC3 = ADC_SC3_CAL;
  __enable_irq();
  while ((ADC0_SC3 & ADC_SC3_CAL) || (ADC1_SC3 & ADC_SC3_CAL)) {
    // wait
  }
  if (ADC0_SC3 & ADC_SC3_CALF) {
    Serial.println("ADC0 calibration failed!");
  } else {
    Serial.println("ADC0 calibration success!");
  }
  if (ADC1_SC3 & ADC_SC3_CALF) {
    Serial.println("ADC1 calibration failed!");
  } else {
    Serial.println("ADC1 calibration success!");
  }
  // handle the calibration outputs (from wait_for_cal() which is static
  __disable_irq();
  uint16_t sum;
  sum = ADC0_CLPS + ADC0_CLP4 + ADC0_CLP3 + ADC0_CLP2 + ADC0_CLP1 + ADC0_CLP0;
  sum = (sum / 2) | 0x8000;
  ADC0_PG = sum;
  sum = ADC0_CLMS + ADC0_CLM4 + ADC0_CLM3 + ADC0_CLM2 + ADC0_CLM1 + ADC0_CLM0;
  sum = (sum / 2) | 0x8000;
  ADC0_MG = sum;
  sum = ADC1_CLPS + ADC1_CLP4 + ADC1_CLP3 + ADC1_CLP2 + ADC1_CLP1 + ADC1_CLP0;
  sum = (sum / 2) | 0x8000;
  ADC1_PG = sum;
  sum = ADC1_CLMS + ADC1_CLM4 + ADC1_CLM3 + ADC1_CLM2 + ADC1_CLM1 + ADC1_CLM0;
  sum = (sum / 2) | 0x8000;
  ADC1_MG = sum;
  __enable_irq();
}

void set_ct(uint8_t ct_value) {
  ct new_ct = cts[ct_value];

  ADC0_SC1A = ADC_SC1_AIEN                                 // interrupt enable
              | ADC_SC1_ADCH(new_ct.adc0.ch);                // input channel, never diff

  ADC1_SC1A = ADC_SC1_AIEN                                 // interrupt enable
              | ADC_SC1_ADCH(new_ct.adc1.ch)                 // input channel
              | ((new_ct.adc1.ch == 0) ? ADC_SC1_DIFF : 0);  // ch0 is diff

  // TODO(truher): these are not channel select per se, on the other hand
  // it's nice for all the CFG2 stuff to be in one place.  hm.
  //          ADC_CFG2_ADACKEN     // 0 => async clock disabled
  //          ADC_CFG2_ADHSC       // 0 => normal conversion speed
  //          ADC_CFG2_ADLSTS(2);  // extra sample time, only with ADLSMP

  ADC0_CFG2 = new_ct.adc0.muxsel ? ADC_CFG2_MUXSEL : 0;
  ADC1_CFG2 = new_ct.adc1.muxsel ? ADC_CFG2_MUXSEL : 0;
//  ADC0_CFG2 = (new_ct.adc0.muxsel ? ADC_CFG2_MUXSEL : 0) | ADC_CFG2_ADHSC;
//  ADC1_CFG2 = (new_ct.adc1.muxsel ? ADC_CFG2_MUXSEL : 0) | ADC_CFG2_ADHSC;

}

void setup() {
  snprintf(uidStr, sizeof(uidStr), "%08lX%08lX", SIM_UIDML, SIM_UIDL);
  Serial.begin(0);
  while (!Serial) {
    // do nothing
  }
  Serial.println("median tests (delete me)");
  int foo[] = {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15};
  Serial.println(median<int>(foo, 5));
  Serial.println(median<int>(foo + 5, 5));
  Serial.println(median<int>(foo + 10, 5));
  Serial.println("median tests done (delete me)");
  Serial.println("Calibrating...");
  calibrate_adc();

  Serial.println("Setup LED...");
  pinMode(pinLED, OUTPUT);
  Serial.println("Setup COCO...");
  pinMode(PIN_ADC_COCO, OUTPUT);

  Serial.println("Setup disable DAC...");
  // i use ADC pins that are also DAC pins, so turn off the DAC
  // TODO: arg, this hangs.  why is that?
  // DAC1_C0 = 0;

  Serial.println("Setup FTM...");
  // FTM SETUP

  FTM1_POL = 0;
  FTM1_OUTMASK = 0xFF;  // mask all
  FTM1_SC = 0x00;       // reset status == turn off FTM
  FTM1_CNT = 0x00;      // zero the counter, or maybe this does nothing
  FTM1_CNTIN = 0;       // counter initial value
//  FTM1_C0SC = FTM_CSC_ELSB | FTM_CSC_MSB;  // output compare, high-true
// ??? TODO ???
  FTM1_C0SC = FTM_CSC_ELSB | FTM_CSC_MSA;  // is the one above wrong?  MSA or MSB?


  Serial.println("Setup frequency...");
  set_frequency(current_frequency);
//
// turn this off to see if it causes the noise?  nope.
  // this is so we can see the clock externally
  PORTA_PCR12 = PORT_PCR_MUX(3)  // ftm1_ch0 goes to K9 in alternative 3
                | PORT_PCR_DSE
                | PORT_PCR_SRE;

  FTM1_EXTTRIG |= FTM_EXTTRIG_INITTRIGEN;  // FTM output trigger enable
  FTM1_MODE |= FTM_MODE_INIT;              // initialize the output

  FTM1_OUTMASK = 0xFE;         // enable only CH0

  // ADC SETUP

  // TODO(truher): something about averaging (see SC3)

  SIM_SOPT7 = SIM_SOPT7_ADC0ALTTRGEN   // enable alternate trigger
              | SIM_SOPT7_ADC1ALTTRGEN
              | SIM_SOPT7_ADC0TRGSEL(9)  // select FTM1 trigger
              | SIM_SOPT7_ADC1TRGSEL(9);

  Serial.println("Setup ct...");
  set_ct(current_ct);

  //          ADC_CFG1_ADLPC       // 0 => normal power configuration
  //        | ADC_CFG1_ADLSMP      // 0 = short sample time, 1 = extra time
  ADC0_CFG1 = ADC_CFG1_ADIV(2)     // 2 => divide by 4, so adck = 15mhz
// something about the clock?
//  ADC0_CFG1 = ADC_CFG1_ADIV(3)
// try more time?
              | ADC_CFG1_ADLSMP
              | ADC_CFG1_MODE(1)     // 12 bit (13b differential)
              | ADC_CFG1_ADICLK(0);  // bus clock (60mhz)
// try bus clock divided by 2
//              | ADC_CFG1_ADICLK(1);

  ADC1_CFG1 = ADC_CFG1_ADIV(2)
// something about the clock?
//  ADC1_CFG1 = ADC_CFG1_ADIV(3)
// try more time?
              | ADC_CFG1_ADLSMP
              | ADC_CFG1_MODE(1)
              | ADC_CFG1_ADICLK(0);
// try bus clock divided by 2
//              | ADC_CFG1_ADICLK(1);


  //         ADC_SC2_REFSEL   // 0 = Vrefh and Vrefl.
  ADC0_SC2 = ADC_SC2_ADTRG    // hardware trigger
             | ADC_SC2_DMAEN;   // dma enable
  ADC1_SC2 = ADC_SC2_ADTRG
             | ADC_SC2_DMAEN;

  //         ADC_SC3_CAL      // start calibration
  //         ADC_SC3_ADCO     // continuous conversion
  //         ADC_SC3_AVGE     // enable averaging
  //         ADC_SC3_AVGS(0)  // 0 => 4 samples
  ADC0_SC3 = 0;  // one-shot, no averaging
  ADC1_SC3 = 0;
//  // try averaging?  this creates more noise, and a different (nonsensical) average (!)
//  ADC0_SC3 = ADC_SC3_AVGE
//             | ADC_SC3_AVGS(0);  
//  ADC1_SC3 = ADC_SC3_AVGE
//             | ADC_SC3_AVGS(0);  

  SIM_SCGC6 |= SIM_SCGC6_FTM1   // ftm1 clock gate
               |  SIM_SCGC6_ADC0;  // adc0 clock gate
  SIM_SCGC3 |= SIM_SCGC3_ADC1;  // adc1 clock gate

  // DMA SETUP

  SIM_SCGC7 |= SIM_SCGC7_DMA;     // enable DMA clock
  SIM_SCGC6 |= SIM_SCGC6_DMAMUX;  // enable DMA MUX clock
  DMA_CR = 0;                     // dma control register

  // DMA SOURCE SETUP

  DMAMUX0_CHCFG0 = DMAMUX_SOURCE_ADC0
                   | DMAMUX_ENABLE;
  DMAMUX0_CHCFG1 = DMAMUX_SOURCE_ADC1
                   | DMAMUX_ENABLE;

  DMA_TCD0_SADDR = &ADC0_RA;       // DMA channel 0 source ADC0 result A
  DMA_TCD1_SADDR = &ADC1_RA;       // DMA channel 1 source ADC1 result A

  DMA_TCD0_SOFF = 0;              // source address offset = 0
  DMA_TCD1_SOFF = 0;
  // read 16 bits at a time from source
  DMA_TCD0_ATTR = DMA_TCD_ATTR_SSIZE(DMA_TCD_ATTR_SIZE_16BIT);
  DMA_TCD1_ATTR = DMA_TCD_ATTR_SSIZE(DMA_TCD_ATTR_SIZE_16BIT);

  DMA_TCD0_SLAST = 0;  // source address adjustment = 0
  DMA_TCD1_SLAST = 0;

  // DMA NBYTES

  DMA_TCD0_NBYTES_MLNO = 2;  // transfer 16 bits
  DMA_TCD1_NBYTES_MLNO = 2;

  // DMA DEST SETUP

  DMA_TCD0_DADDR = buffer0;  // destination address
  DMA_TCD1_DADDR = buffer1;

  DMA_TCD0_DOFF = 2;         // increment 16 bits
  DMA_TCD1_DOFF = 2;
  // write 16 bits at a time to dest
  DMA_TCD0_ATTR |= DMA_TCD_ATTR_DSIZE(DMA_TCD_ATTR_SIZE_16BIT);
  DMA_TCD1_ATTR |= DMA_TCD_ATTR_DSIZE(DMA_TCD_ATTR_SIZE_16BIT);

  Serial.println("Setup length...");
  set_length(current_length);

  DMA_TCD0_CSR = DMA_TCD_CSR_DREQ       // disable on completion
                 | DMA_TCD_CSR_INTMAJOR;  // interrupt on completion
  DMA_TCD1_CSR = DMA_TCD_CSR_DREQ
                 | DMA_TCD_CSR_INTMAJOR;

  // DMA ENABLE
  Serial.println("Enable DMA...");

  DMA_SERQ = 0;  // enable DMA channel 0
  DMA_SERQ = 1;  // enable DMA channel 1

  // RESULT INTERRUPT

  NVIC_ENABLE_IRQ(IRQ_DMA_CH0);
  NVIC_ENABLE_IRQ(IRQ_DMA_CH1);

  // ADC interrupt (to see it on the pin)
  NVIC_ENABLE_IRQ(IRQ_ADC0);
  NVIC_ENABLE_IRQ(IRQ_ADC1);
  Serial.println("Setup complete!");
}


// figure out how to receive commands
//
// {c}{n}\r
//
// where {c} is one of:
//
//   F = frequency in hz
//   C = channel number, or zero to scan
//   L = length in samples
//
// and {n} is an int

char cmd_buffer[100];

void loop() {
  if (Serial.available()) {
    size_t bytes_read =
      Serial.readBytesUntil('\r', cmd_buffer, sizeof(cmd_buffer) - 1);
    if (bytes_read < 1) return;
    cmd_buffer[bytes_read] = '\0';
    switch (*cmd_buffer) {
      case 'C': {
          Serial.print("found C: ");
          if (bytes_read < 2) break;
          int channel = atoi(cmd_buffer + 1);
          if (channel < 0) break;
          new_channel = channel;
          Serial.print("accepted new channel: ");
          Serial.print(new_channel);
          Serial.println();
          break;
        }
      case 'F': {
          Serial.print("found F: ");
          if (bytes_read < 2) break;
          int frequency = atoi(cmd_buffer + 1);
          if (frequency <= 0) break;
          new_frequency = frequency;
          Serial.print("accepted new frequency: ");
          Serial.print(new_frequency);
          Serial.println();
          break;
        }
      case 'L': {
          Serial.print("found L: ");
          if (bytes_read < 2) break;
          int length = atoi(cmd_buffer + 1);
          if (length <= 0) break;
          if (length > 65535) break;
          new_length = length;
          Serial.print("accepted new length: ");
          Serial.print(new_length);
          Serial.println();
          break;
        }
      default:
        Serial.print("unrecognized command: ");
        Serial.println(cmd_buffer);
    }
  }
}

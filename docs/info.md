<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

This is going to be my UW ASIC onboarding project, making and using the SPI protocol. It reads the COPI data 1 bit at a time, then parse the 16 bits of COPI data and split it into a READ/WRITE signal, ADDRESS bits, and the DATA bits.

## How to test

To test this project, I'm going to first test out the SPI protocol and give it both valid and invalid data. To test the PWM peripheral, I test it's frequency by calculating 1/period, then I test the duty cycle of the PWM with various percentages like 0%, 50%, and 100%.

## External hardware

List external hardware used in your project (e.g. PMOD, LED display, etc), if any.

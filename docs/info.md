<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

The peripheral index is the number TinyQV will use to select your peripheral.  You will pick a free
slot when raising the pull request against the main TinyQV repository, and can fill this in then.  You
also need to set this value as the PERIPHERAL_NUM in your test script.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

# Pulse Transmitter

Author: Han

Peripheral index: 11

## What it does
Pulse transmitter is a versatile peripheral that can transmit digital waveforms of various durations, with optional support for carrier modulation. As such, various schemes like Pulse Distance, Pulse Width, Manchester encoding, etc. can be implemented. This makes it ideal for remote control transmitter applications. However, it can also be used to drive other devices like the WS2812B addressable LED.

### Specifications
- 256 bits of program data memory
- 24 bit duration timer (8 bit with prescaler)
- 12 bit carrier timer
- 9 bit program counter
- 7 bit loop counter
- 4 interrupts (that can be configured)

### Modes of operation
Due to the limited amount of resources available, you can operate the pulse transmitter in 2 modes.

| Mode                     | Description                                                                                       |
|--------------------------|---------------------------------------------------------------------------------------------------|
| 1bps (1 bits per symbol) | Support up to 256 symbols, each 1-bit symbol is expanded to 2 2-bit symbols via a lookup table.               |
| 2bps (2 bits per symbol) | Support up to 128 symbols                                                                         |

Each symbol is encoded as follows, in 2bps mode, you directly write this to the to the program data memory.
| Bit 1          | Bit 0           |
|----------------|-----------------|
| TRANSMIT_LEVEL | DURATION_SELECT |

In 1bps mode, each symbol is expanded to 2 symbols.
| Value  | Symbol 1    |  Symbol 2  |
|--------|-------------|-------------|
| 0      | 2 bit value | 2 bit value |
| 1      | 2 bit value | 2 bit value |

### Extra features
You can specify at what position in the buffer the program starts, stops, or loopback to. You can choose to not loop, loop up to 128 times or loop forever.
 
For the first 8 symbols at address 0x00, a 8 bit `auxillary_mask` is also available. Together, a 8 bit duration can be selected from one of the six lookup tables.

| Auxillary Bit | Symbol Bit 1 | Symbol Bit 0 | Evaluated Duration   |
|---------------|--------------|--------------|----------------------|
| 0             | 0            | 0            | main_low_duration_a  |
| 0             | 0            | 1            | main_low_duration_b  |
| 0             | 1            | 0            | main_high_duration_a |
| 0             | 1            | 1            | main_high_duration_b |
| 1             | X            | 0            | auxillary_duration_a |
| 1             | X            | 1            | auxillary_duration_b |

There is also a 4 bit prescaler value each for main and auxillary.
Combined together, total duration ticks = (duration + 2) << prescaler.

## Register map
| Address     | Name  | Access | Description      |
|-------------|-------|--------|------------------|
| 0x00        | DATA  | W*     | REG_0            |
| 0x04        | DATA  | W      | REG_1            |
| 0x08        | DATA  | W      | REG_2            |
| 0x0C        | DATA  | W      | REG_3            |
| 0x10        | DATA  | W      | REG_4            |
| 0x20 - 0x3F | DATA  | W      | PROGRAM_DATA_MEM |

The 5 configuration registers are initialized to 0. 

For the program memory, the initial value is undefined.

## Writing
Only aligned 32 bit writes are supported in general. However, 8 bit write is allowed at address 0x00 to aid in clearing interrupts, starting or stopping the program.

### REG_0
| Bits  | Name                                |
|-------|-------------------------------------|
| 0     | clear_timer_interrupt               |
| 1     | clear_loop_interrupt                |
| 2     | clear_program_end_interrupt         |
| 3     | clear_program_counter_mid_interrupt |
| 4     | start_program                       |
| 5     | stop_program                        |
| 7:6   | *unused*                            |
| 8     | timer_interrupt_en                  |
| 9     | loop_interrupt_en                   |
| 10    | program_end_interrupt_en            |
| 11    | program_counter_mid_interrupt_en    |
| 12    | loop_forever                        |
| 13    | idle_level                          |
| 14    | invert_output                       |
| 15    | carrier_en                          |
| 16    | use_2bps                            |
| 18:17 | low_symbol_0                        |
| 20:19 | low_symbol_1                        |
| 22:21 | high_symbol_0                       |
| 24:23 | high_symbol_1                       |
| 31:25 | *unused*                            |

To clear interrupts, start or stop the program, simply write a '1' to corresponding bit.

### REG_1
| Bits  | Name                                |
|-------|-------------------------------------|
| 7:0   | program_start_index                 |
| 15:8  | program_end_index                   |
| 23:16 | program_end_loopback_index          |
| 30:24 | program_loop_count (7 bits)         |
| 31    | *unused*                            |

### REG_2
| Bits  | Name                                |
|-------|-------------------------------------|
| 7:0   | main_low_duration_a                 |
| 15:8  | main_low_duration_b                 |
| 23:16 | main_high_duration_a                |
| 31:24 | main_high_duration_b                |

### REG_3
| Bits  | Name                                |
|-------|-------------------------------------|
| 7:0   | auxillary_mask                      |
| 15:8  | auxillary_duration_a                |
| 23:16 | auxillary_duration_b                |
| 27:24 | auxillary_prescaler                 |
| 31:28 | main_prescaler                      |

### REG_4
| Bits  | Name                                |
|-------|-------------------------------------|
| 11:0  | carrier_duration (12 bits)          |
| 31:12 | *unused*                            |

## Reading
Read address does not matter as a fixed 32 bits of data are assigned to the `data_out` register. The bottom 8, 16 or all 32 bits are valid on read.
| Bits  | Name                                 |
|-------|--------------------------------------|
| 0     | timer_interrupt_status               |
| 1     | loop_interrupt_status                |
| 2     | program_end_interrupt_status         |
| 3     | program_counter_mid_interrupt_status |
| 4     | program_status                       |
| 7:5   | *unused* (value of 0)                |
| 14:8  | program_counter                      |
| 15    | *unused* (value of 0)                |
| 24:16 | full_program_loop_counter (9 bits)   |
| 31:25 | *unused* (value of 0)                |

## How to test

## External hardware
You may wish to test with a IR LED, the output pins cannot deliver much current, so use a buffer or transistor to drive the LED.
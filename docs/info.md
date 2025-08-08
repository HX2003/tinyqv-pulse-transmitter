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

Pulse transmitter is a peripheral that can transmit up to 128 binary symbols, each having varying durations. You can specify at what position in the buffer the program starts, stops, or loopback to. You can choose to not loop, loop up to 256 times or loop forever.

Due to the limited amount of memory available, each symbol is encoded as follows:
| Bit 1          | Bit 0           |
|----------------|-----------------|
| TRANSMIT_LEVEL | DURATION_SELECT |

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
| 0x00        | DATA  | R*/W*  | REG_0            |
| 0x04        | DATA  | W      | REG_1            |
| 0x08        | DATA  | W      | REG_2            |
| 0x0C        | DATA  | W      | REG_3            |
| 0x20 - 0x3F | DATA  | W      | PROGRAM_DATA_MEM |

## Writing
Only aligned 32 bit writes are supported in general. However, 8 bit write is allowed at address 0x00 to aid in clearing interrupts, starting or stopping the program.

### REG_0
| Bits  | Name                                |
|-------|-------------------------------------|
| 0     | clear_timer_interrupt               |
| 1     | clear_loop_interrupt                |
| 2     | clear_program_end_interrupt         |
| 3     | clear_counter_64_interrupt          |
| 4     | start_program                       |
| 5     | stop_program                        |
| 7:6   | *unused*                            |
| 8     | timer_interrupt_en                  |
| 9     | loop_interrupt_en                   |
| 10    | program_end_interrupt_en            |
| 11    | program_counter_64_interrupt_en     |
| 12    | loop_forever                        |
| 13    | idle_level                          |
| 14    | invert_output                       |
| 15    | carrier_en                          |

To clear interrupts, start or stop the program, simply write a '1' to corresponding bit.

### REG_1
| Bits  | Name                                |
|-------|-------------------------------------|
| 6:0   | program_start_index                 |
| 7     | *unused*                            |
| 14:8  | program_end_index                   |
| 15    | *unused*                            |
| 23:16 | program_end_loop_count              |
| 30:24 | program_end_loopback_index          |
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
| 15:0  | carrier_duration                    |
| 31:16 | *unused*                            |

## Reading
Read address does not matter as a fixed 32 bits of data are assigned to the `data_out` register. The bottom 8, 16 or all 32 bits are valid on read.
| Bits  | Name                                |
|-------|-------------------------------------|
| 0     | timer_interrupt_status              |
| 1     | loop_interrupt_status               |
| 2     | program_end_interrupt_status        |
| 3     | program_counter_64_interrupt_status |
| 4     | program_status                      |
| 7:5   | *unused* (value of 0)               |
| 14:8  | program_counter                     |
| 15    | *unused* (value of 0)               |
| 24:16 | program_loop_counter (9 bits)       |
| 31:25 | *unused* (value of 0)               |

## How to test

## External hardware
You may wish to test with a IR LED, I'm not sure about the current limits of the output pins, so use a buffer or transistor to drive the LED.
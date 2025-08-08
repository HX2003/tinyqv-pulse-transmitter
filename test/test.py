# SPDX-FileCopyrightText: © 2025 HX2003
# SPDX-License-Identifier: Apache-2.0

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, FallingEdge, Edge

from tqv import TinyQV

# When submitting your design, change this to the peripheral number
# in peripherals.v.  e.g. if your design is i_user_peri05, set this to 5.
# The peripheral number is not used by the test harness.
PERIPHERAL_NUM = 11

MAX_DURATION = 255 # max duration you can put in the duration field
MAX_PROGRAM_LEN = 128 # must be power of 2 as this also affects the rollover / wrapping

MAX_PROGRAM_1BPS_LEN = 256 # must be power of 2 as this also affects the rollover / wrapping
MAX_PROGRAM_2BPS_LEN = MAX_PROGRAM_1BPS_LEN >> 1 # divide by 2
MAX_INTERNAL_PROGRAM_LEN = MAX_PROGRAM_1BPS_LEN * 2
# Note that with 2bps,
# you need to multiply program_start_index, program_end_index, program_end_loopback_index by 2

MAX_PROGRAM_LOOP_LEN = 128 # the actual value set is MAX_PROGRAM_LOOP_LEN - 1
MAX_TEST_INFINITE_LOOP_LEN = 100

class Device:
    def __init__(self, dut):
        self.dut = dut
        self.reset_config()
    
    async def init(self):
        # We target the clock period to 15.625 ns (64 MHz)
        clock = Clock(self.dut.clk, 15, units="ns")  # test at 66 MHz, close enough to 64MHz
        cocotb.start_soon(clock.start())

        # Interact with your design's registers through this TinyQV class.
        # This will allow the same test to be run when your design is integrated
        # with TinyQV - the implementation of this class will be replaces with a
        # different version that uses Risc-V instructions instead of the SPI test
        # harness interface to read and write the registers.
        self.tqv = TinyQV(self.dut, PERIPHERAL_NUM)

        # Reset
        await self.tqv.reset()
         
    # only sets the member variables, does not actually write to the device
    def reset_config(self):
        self._clear_timer_interrupt = 0
        self._clear_loop_interrupt = 0
        self._clear_program_end_interrupt = 0
        self._clear_program_counter_mid_interrupt = 0
        self._start_program = 0
        self._stop_program = 0

        self.config_timer_interrupt_en = 0
        self.config_loop_interrupt_en = 0
        self.config_program_end_interrupt_en = 0
        self.config_program_counter_mid_interrupt_en = 0
        self.config_loop_forever = 0
        self.config_idle_level = 0
        self.config_invert_output = 0
        self.config_carrier_en = 0
        self.config_use_2bps = 1 # set this to one first
        self.config_low_symbol_0 = 0
        self.config_low_symbol_1 = 0
        self.config_high_symbol_0 = 0
        self.config_high_symbol_1 = 0

        self.config_program_start_index = 0
        self.config_program_end_index = 0
        self.config_program_loopback_index = 0
        self.config_program_loop_count = 0
        
        self.config_main_low_duration_a = 0
        self.config_main_low_duration_b = 0
        self.config_main_high_duration_a = 0
        self.config_main_high_duration_b = 0
        
        self.config_auxillary_mask = 0
        self.config_auxillary_duration_a = 0
        self.config_auxillary_duration_b = 0
        self.config_auxillary_prescaler = 0
        self.config_main_prescaler = 0

        self.config_carrier_duration = 0
         

    async def write8_reg_0(self):
        reg0 = self._gen_reg_0()
        await self.tqv.write_byte_reg(0, reg0 & 0xFF)

    async def write32_reg_0(self):
        reg0 = self._gen_reg_0()
        await self.tqv.write_word_reg(0, reg0)
    
    def _gen_reg_0(self):
        return self._clear_timer_interrupt \
            | (self._clear_loop_interrupt << 1) \
            | (self._clear_program_end_interrupt << 2) \
            | (self._clear_program_counter_mid_interrupt << 3) \
            | (self._start_program << 4) \
            | (self._stop_program << 5) \
            | (self.config_timer_interrupt_en << 8) \
            | (self.config_loop_interrupt_en << 9) \
            | (self.config_program_end_interrupt_en << 10) \
            | (self.config_program_counter_mid_interrupt_en << 11) \
            | (self.config_loop_forever << 12) \
            | (self.config_idle_level << 13) \
            | (self.config_invert_output << 14) \
            | (self.config_carrier_en << 15) \
            | (self.config_use_2bps << 16) \
            | (self.config_low_symbol_0 << 17) \
            | (self.config_low_symbol_1 << 19) \
            | (self.config_high_symbol_0 << 21) \
            | (self.config_high_symbol_1 << 23) \
            
    async def write32_reg_1(self):
        reg1 = self.config_program_start_index \
            | (self.config_program_end_index << 8) \
            | (self.config_program_loopback_index << 16) \
            | (self.config_program_loop_count << 24) \
        
        await self.tqv.write_word_reg(4, reg1)

    async def write32_reg_2(self):
        reg2 = (self.config_main_high_duration_b << 24) | (self.config_main_high_duration_a << 16) | (self.config_main_low_duration_b << 8) | self.config_main_low_duration_a
        await self.tqv.write_word_reg(8, reg2)
    
    async def write32_reg_3(self):
        reg3 = self.config_auxillary_mask \
            | (self.config_auxillary_duration_a << 8) \
            | (self.config_auxillary_duration_b << 16) \
            | (self.config_auxillary_prescaler << 24) \
            | (self.config_main_prescaler << 28)
        
        await self.tqv.write_word_reg(12, reg3)

    async def write32_reg_4(self):
        reg4 = self.config_carrier_duration
        
        await self.tqv.write_word_reg(16, reg4)

    """ Start the program """
    async def start_program(self):
        self._start_program = 1
        await self.write8_reg_0()
        self._start_program = 0

    """ Stop the program """
    async def stop_program(self):
        self._stop_program = 1
        await self.write8_reg_0()
        self._stop_program = 0

    """ Clear the desired interrupts using 8 bit write """
    async def clear_interrupts(self, clear_timer_interrupt = 1, clear_loop_interrupt = 1, clear_program_end_interrupt=1, clear_program_counter_mid_interrupt=1):
        self._clear_timer_interrupt = clear_timer_interrupt
        self._clear_loop_interrupt = clear_loop_interrupt
        self._clear_program_end_interrupt = clear_program_end_interrupt
        self._clear_program_counter_mid_interrupt = clear_program_counter_mid_interrupt
        self._start_program = 0
        self._stop_program = 0

        await self.write8_reg_0()

        self._clear_timer_interrupt = 0
        self._clear_loop_interrupt = 0
        self._clear_program_end_interrupt = 0
        self._clear_program_counter_mid_interrupt = 0
        self._start_program = 0
        self._stop_program = 0

    """ Clear the desired interrupts using 8 bit write """
    async def clear_interrupts_using32(self, clear_timer_interrupt = 1, clear_loop_interrupt = 1, clear_program_end_interrupt=1, clear_program_counter_mid_interrupt=1):
        self._clear_timer_interrupt = clear_timer_interrupt
        self._clear_loop_interrupt = clear_loop_interrupt
        self._clear_program_end_interrupt = clear_program_end_interrupt
        self._clear_program_counter_mid_interrupt = clear_program_counter_mid_interrupt
        self._start_program = 0
        self._stop = 0

        await self.write32_reg_0()

        self._clear_timer_interrupt = 0
        self._clear_loop_interrupt = 0
        self._clear_program_end_interrupt = 0
        self._clear_program_counter_mid_interrupt = 0
        self._start_program = 0
        self._stop_program = 0

    # for a symbol tuple[int, int], 
    # the first value is the duration selector
    # the second value is the transmit level
    async def write_program(self, program: list[tuple[int, int]]):
        # We did not check if the program is currently running, 
        # writing while program is running may have undefined behaviour

        await self.write32_reg_0()
        await self.write32_reg_1()
        await self.write32_reg_2()
        await self.write32_reg_3()
        await self.write32_reg_4()

        word = 0
        count = 0
        i = 0
        
        for symbol_duration_selector, symbol_transmit_level in program:
            symbol_data = (symbol_transmit_level << 1 ) | symbol_duration_selector

            word |= symbol_data << (i * 2)
            i += 1

            if i == 16:
                await self.tqv.write_word_reg(0b100000 | count, word)
                word = 0
                i = 0
                count += 4

        # Write the remaining bits
        if i > 0:
            await self.tqv.write_word_reg(0b100000 | count, word)

    
    # In 2bps mode,
    # each symbol is 2 bits
    async def test_expected_waveform_2bps(self, program: list[tuple[int, int]]):
        assert len(program) <= MAX_PROGRAM_2BPS_LEN

        # We pre-generate the duration and expected output level (before inversion) in a 2-tuple
        waveform = []
        for i, symbol in enumerate(program):
            symbol_duration_selector = symbol[0]
            symbol_transmit_level = symbol[1]
            symbol_data = (symbol_transmit_level << 1 ) | symbol_duration_selector

            if i < 8 and (self.config_auxillary_mask & (1 << i)):
                prescaler = self.config_auxillary_prescaler
                if(symbol_duration_selector == 0):
                    duration = self.config_auxillary_duration_a
                else:
                    duration = self.config_auxillary_duration_b
            else:
                prescaler = self.config_main_prescaler
                match (symbol_data):
                    case 0: duration = self.config_main_low_duration_a
                    case 1: duration = self.config_main_low_duration_b
                    case 2: duration = self.config_main_high_duration_a
                    case 3: duration = self.config_main_high_duration_b
            
            expected_output = symbol_transmit_level ^ self.config_invert_output
            expected_duration = (duration + 2) << prescaler
            waveform.append((expected_duration, expected_output))

        await self._test_expected_waveform(waveform)

    # In 1bps mode,
    # each symbol is 1 bit
    async def test_expected_waveform_1bps(self, program: list[tuple[int]]):
        assert len(program) <= MAX_PROGRAM_1BPS_LEN
        
        # We pre-generate the duration and expected output level (before inversion) in a 2-tuple
        # Note that we expand our program, so the len(waveform) is twice the len(program)
        waveform = []

        await self._test_expected_waveform(waveform)
    
    
    # example waveform [(2, 1), (3, 0), (4, 1), (4, 1), (5, 0)] 
    async def _test_expected_waveform(self, waveform: list[tuple[int, int]]):
        # config_carrier_en must be 0, generation of expected_waveform not supported with this parameter
        assert not self.config_carrier_en

        # lets start the test
        # the program must be already configured
        # Must run concurrently
        cocotb.start_soon(self.start_program()) #await self.start_program()

        # Wait until valid output goes high
        while(self.dut.uo_out[3].value == 0):
            await ClockCycles(self.dut.clk, 1)

        #await RisingEdge(self.dut.test_harness.user_peripheral.valid_output)

        
        # when config_program_loop_count = 0, the program executes once
        # when config_program_loop_count = 1, the program executes twice
        # and so on...
        if(self.config_loop_forever):
            self.dut._log.info(f'config_loop_forever is enabled, but we will only test for {MAX_TEST_INFINITE_LOOP_LEN} number of loops')
            program_loop_counter = MAX_TEST_INFINITE_LOOP_LEN
        else:
            program_loop_counter = self.config_program_loop_count + 1
        
        waveform_len = len(waveform)
        output_valid = True

        # The internal program counter is between 0 and 511
        # In 2bps (2 bits per symbol) mode, program_counter is incremented by 4 each time
        # In 1bps (1 bits per symbol) mode, program_counter is incremented by 1 each time

        internal_program_counter = self.config_program_start_index * 2

        while(output_valid):
            if (self.config_use_2bps):
                assert (internal_program_counter >> 2) < waveform_len # make sure don't access out of bounds
                assert internal_program_counter % 4 == 0 # should be a multiple of 4

                duration = waveform[internal_program_counter >> 2][0]
                expected_level = waveform[internal_program_counter >> 2][1]
            else:
                assert internal_program_counter < waveform_len # make sure don't access out of bounds
                duration = waveform[internal_program_counter][0]
                expected_level = waveform[internal_program_counter][1]

            for i in range(duration): # check every cycle for thoroughness
                assert self.dut.uo_out[4].value == expected_level
                await ClockCycles(self.dut.clk, 1) 

            if(internal_program_counter == self.config_program_end_index * 2):
                program_loop_counter -= 1
                
                if(program_loop_counter > 0):
                    internal_program_counter = self.config_program_loopback_index * 2
                else:
                    output_valid = False
            else:
                if (self.config_use_2bps):
                    internal_program_counter += 4
                else:
                    internal_program_counter += 1
                
                # Simulate rollover / wrapping
                if(internal_program_counter >= MAX_INTERNAL_PROGRAM_LEN):
                    internal_program_counter = 0
        
        if(not self.config_loop_forever): # do not check if config_loop_forever is enabled
            # lets check the idle state is correct for the next n number of cycles for good measure
            total_duration = 999
            for w in waveform:
                duration = w[0]
                total_duration += duration

            for i in range(total_duration):
                assert self.dut.uo_out[4].value == (self.config_idle_level ^ self.config_invert_output)
                await ClockCycles(self.dut.clk, 1)

# Basic test
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_test1(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_high_duration_a = 0

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Basic test
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_test2(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_high_duration_a = 157

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Basic test
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_test3(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 3

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Basic test with output inverted
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_test4(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_invert_output = 1
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Basic test
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_test5(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 1), (1, 1), (1, 0)]
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 13
    device.config_main_low_duration_b = 34
    device.config_main_high_duration_a = 10
    device.config_main_high_duration_b = 10

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Basic test
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_test6(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 1), (1, 1), (0, 0), (0, 0), (1, 0), (0, 1)]
    
    device.config_program_end_index = (len(program) - 1) * 2
    
    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Basic test with idle level
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_test7(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 1), (1, 1), (0, 0), (0, 0), (1, 0), (0, 1)]
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_idle_level = 1
    
    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Basic test with prescaler
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_test8(dut):
    device = Device(dut)
    await device.init()

    program = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 2
    device.config_main_low_duration_b = 0
    device.config_main_high_duration_a = 4
    device.config_main_high_duration_b = 6
    device.config_main_prescaler = 1

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Basic test with prescaler
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_test9(dut):
    device = Device(dut)
    await device.init()

    program = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 2
    device.config_main_low_duration_b = 0
    device.config_main_high_duration_a = 4
    device.config_main_high_duration_b = 6
    device.config_main_prescaler = 2

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Basic test with bigger prescaler
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_test10(dut):
    device = Device(dut)
    await device.init()

    program = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2
    device.config_main_prescaler = 9

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Basic test to test that config_program_end_index is respected
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_test11(dut):
    device = Device(dut)
    await device.init()

    program = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2

    # fill in the rest of the buffer with some data
    program_with_extras = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0), (1, 0), (0, 1), (0, 0), (1, 1), (1, 0), (0, 0), (1, 1), (1, 0), (1, 0), (0, 1)]
    await device.write_program(program_with_extras)

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Basic test to test that config_program_start_index is respected
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_test12(dut):
    device = Device(dut)
    await device.init()

    program = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_program_start_index = 3 * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Basic test rollover / wrapping test
# It starts at config_program_start_index, rolls over, 
# and terminates at config_program_end_index without looping
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_test13(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_LEN
    
    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_program_start_index = 77 * 2
    device.config_program_end_index = 33 * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Basic test MAX_PROGRAM_LEN number of symbols
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def basic_test14(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_LEN
    
    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Basic test MAX_PROGRAM_LEN number of symbols with prescaler
@cocotb.test(timeout_time=11, timeout_unit="ms")
async def basic_test15(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_LEN
    
    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_main_prescaler = 3

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Basic test with infinite loop
@cocotb.test(timeout_time=11, timeout_unit="ms")
async def basic_test16(dut):
    device = Device(dut)
    await device.init()

    program = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_main_prescaler = 3
    device.config_loop_forever = 1

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Basic test with MAX_DURATION
@cocotb.test(timeout_time=11, timeout_unit="ms")
async def basic_test17(dut):
    device = Device(dut)
    await device.init()

    program = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = MAX_DURATION
    device.config_main_low_duration_a = 242
    device.config_main_high_duration_b = MAX_DURATION
    device.config_main_high_duration_a = 193

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)


# Advanced test with looping a certain number of counts
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_test1(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 1

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with looping a certain number of counts
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_test2(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 2

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with looping a certain number of counts
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_test3(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 45

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with looping MAX_PROGRAM_LOOP_LEN times
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_test4(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = MAX_PROGRAM_LOOP_LEN - 1

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with looping a certain number of counts
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_test5(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 1

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with looping a certain number of counts
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_test6(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 2

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with looping a certain number of counts
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_test7(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 45

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with looping MAX_PROGRAM_LOOP_LEN times
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_test8(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = MAX_PROGRAM_LOOP_LEN - 1

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with looping a certain number of counts with prescaler
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_test9(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 1
    device.config_main_prescaler = 1

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with looping a certain number of counts with prescaler
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_test10(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 2
    device.config_main_prescaler = 1

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with looping a certain number of counts with prescaler
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_test11(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 45
    device.config_main_prescaler = 1

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with looping MAX_PROGRAM_LOOP_LEN times with prescaler
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_test12(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = MAX_PROGRAM_LOOP_LEN - 1
    device.config_main_prescaler = 1

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with looping a certain number of counts with prescaler
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_test13(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 1
    device.config_main_prescaler = 1

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with looping a certain number of counts with prescaler
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_test14(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 2
    device.config_main_prescaler = 1

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with looping a certain number of counts with prescaler
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_test15(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 45
    device.config_main_prescaler = 1

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with looping MAX_PROGRAM_LOOP_LEN times
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_test16(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = MAX_PROGRAM_LOOP_LEN - 1

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with looping a certain number of counts, with MAX_PROGRAM_LEN number of symbols
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def advanced_test17(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_LEN
    
    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 1
    device.config_main_low_duration_a = 2
    device.config_main_high_duration_b = 3
    device.config_main_high_duration_a = 4
    device.config_program_loop_count = 1

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with looping a certain number of counts, with MAX_PROGRAM_LEN number of symbols
@cocotb.test(timeout_time=15, timeout_unit="ms")
async def advanced_test18(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_LEN
    
    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 0
    device.config_main_low_duration_a = 1
    device.config_main_high_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_program_loop_count = 23

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with looping a MAX_PROGRAM_LOOP_LEN times, with MAX_PROGRAM_LEN number of symbols
@cocotb.test(timeout_time=15, timeout_unit="ms")
async def advanced_test19(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_LEN
    
    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 0
    device.config_main_low_duration_a = 1
    device.config_main_high_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_program_loop_count = MAX_PROGRAM_LOOP_LEN - 1

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with auxillary duration
@cocotb.test(timeout_time=15, timeout_unit="ms")
async def advanced_test20(dut):
    device = Device(dut)
    await device.init()

    program = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0), (1, 0), (0, 1), (0, 0), (1, 1), (1, 0), (0, 0), (1, 1), (1, 0), (1, 0), (0, 1)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 0
    device.config_main_low_duration_a = 1
    device.config_main_high_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_auxillary_duration_a = 42
    device.config_auxillary_duration_b = 98
    device.config_auxillary_mask = 0b10101010
     
    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with auxillary duration and auxillary prescaler
@cocotb.test(timeout_time=15, timeout_unit="ms")
async def advanced_test21(dut):
    device = Device(dut)
    await device.init()

    program = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0), (1, 0), (0, 1), (0, 0), (1, 1), (1, 0), (0, 0), (1, 1), (1, 0), (1, 0), (0, 1)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 0
    device.config_main_low_duration_a = 1
    device.config_main_high_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_auxillary_duration_a = 4 #33
    device.config_auxillary_duration_b = 4 #127
    device.config_auxillary_prescaler = 1
    device.config_auxillary_mask = 0b10101010
     
    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Advanced test with auxillary duration and larger auxillary prescaler
@cocotb.test(timeout_time=15, timeout_unit="ms")
async def advanced_test22(dut):
    device = Device(dut)
    await device.init()

    program = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0), (1, 0), (0, 1), (0, 0), (1, 1), (1, 0), (0, 0), (1, 1), (1, 0), (1, 0), (0, 1)]

    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_b = 0
    device.config_main_low_duration_a = 1
    device.config_main_high_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_auxillary_duration_a = 33
    device.config_auxillary_duration_b = 127
    device.config_auxillary_prescaler = 6
    device.config_auxillary_mask = 0b10101010
     
    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Elite test with looping and config_program_loopback_index set to exactly the (len(program) - 1) * 2
# So it should run from 0 to (len(program) - 1) * 2, then the last symbol is repeatedly sent
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def elite_test1(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 0), (1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2
    device.config_program_loop_count = 10
    device.config_program_loopback_index = (len(program) - 1) * 2

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Elite test with looping and config_program_loopback_index set to exactly the (len(program) - 2) * 2
# So it should run from 0 to (len(program) - 1) * 2 then the last 2 symbols is repeatedly sent
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def elite_test2(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 0), (1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2
    device.config_program_loop_count = 10
    device.config_program_loopback_index = (len(program) - 2) * 2

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Elite test with looping and config_program_loopback_index set to exactly to 1 * 2
# So it should run from 0 to (len(program) - 1) * 2, then the last len(program) - 1 number of symbols is repeatedly sent
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def elite_test3(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 0), (1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2
    device.config_program_loop_count = 10
    device.config_program_loopback_index = 1 * 2

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Elite test with looping and config_program_loopback_index set to exactly the (len(program) - 1) * 2, with MAX_PROGRAM_LEN number of symbols
# So it should run from 0 to (len(program) - 1) * 2, then the last symbol is repeatedly sent
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def elite_test4(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_LEN

    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2
    device.config_program_loop_count = 55
    device.config_program_loopback_index = (len(program) - 1) * 2

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Elite test with looping and config_program_loopback_index set to exactly the (len(program) - 2) * 2, with MAX_PROGRAM_LEN number of symbols
# So it should run from 0 to (len(program) - 1) * 2 then the last 2 symbols is repeatedly sent
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def elite_test5(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_LEN

    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2
    device.config_program_loop_count = 55
    device.config_program_loopback_index = (len(program) - 2) * 2

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)
 

# Elite test with rollover / wrapping, with auxillary prescaler and auxillary duration
# It starts at config_program_start_index, rolls over,
# and terminates at config_program_end_index without looping
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def elite_test6(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_LEN

    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_program_start_index = 100 * 2
    device.config_program_end_index = 33 * 2
    device.config_main_low_duration_a = 15
    device.config_main_low_duration_b = 35
    device.config_main_high_duration_a = 10
    device.config_main_high_duration_b = 55
    device.config_auxillary_mask = 0b00000001
    device.config_auxillary_duration_b = 100
    device.config_auxillary_duration_a = 50
    device.config_auxillary_prescaler = 3

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Elite test with rollover / wrapping, with auxillary prescaler and auxillary duration
# It starts at config_program_start_index, rolls over,
# and terminates at config_program_end_index without looping
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def elite_test7(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_LEN

    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_program_start_index = 100 * 2
    device.config_program_end_index = 33 * 2
    device.config_main_low_duration_a = 15
    device.config_main_low_duration_b = 35
    device.config_main_high_duration_a = 10
    device.config_main_high_duration_b = 55
    device.config_auxillary_mask = 0b00111100
    device.config_auxillary_duration_b = 100
    device.config_auxillary_duration_a = 50
    device.config_auxillary_prescaler = 3

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

# Interrupt disable test - do not enable interrupts,
# but we loop, have program counter past 64
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def interrupt_test1(dut):
    device = Device(dut)
    await device.init()

    program = []

    random.seed(1234) 
    for _ in range(96):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 3
    device.config_program_loop_count = 4

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

    assert not await device.tqv.is_interrupt_asserted()

# Program end interrupt test, using 8 bit write to clear
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def interrupt_test2(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_program_end_interrupt_en = 1
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 3

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

    assert await device.tqv.is_interrupt_asserted()

    await device.clear_interrupts(
        clear_timer_interrupt = 1,
        clear_loop_interrupt = 1,
        clear_program_end_interrupt = 0,  # Means no effect (don't clear program end interrupt)
        clear_program_counter_mid_interrupt = 1
    )
    # there should be no effect, program end interrupt interrupt should not be cleared
    assert await device.tqv.is_interrupt_asserted()

    await device.clear_interrupts(
        clear_timer_interrupt = 0,
        clear_loop_interrupt = 0,
        clear_program_end_interrupt = 1,
        clear_program_counter_mid_interrupt = 0
    )

    assert not await device.tqv.is_interrupt_asserted()

# Program end interrupt test using 32 bit write to clear
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def interrupt_test3(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_program_end_interrupt_en = 1
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 3

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

    assert await device.tqv.is_interrupt_asserted()

    await device.clear_interrupts_using32(
        clear_timer_interrupt = 1,
        clear_loop_interrupt = 1,
        clear_program_end_interrupt = 0, # Means no effect (don't clear timer interrupt)
        clear_program_counter_mid_interrupt = 1
    )

    # there should be no effect
    assert await device.tqv.is_interrupt_asserted()
    
    await device.clear_interrupts_using32(
        clear_timer_interrupt = 0,
        clear_loop_interrupt = 0,
        clear_program_end_interrupt = 1,
        clear_program_counter_mid_interrupt = 0
    )
    assert not await device.tqv.is_interrupt_asserted()

# Loop interrupt test
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def interrupt_test4(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_loop_interrupt_en = 1
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 3

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

    # No interrupt triggered because we did not loop
    assert not await device.tqv.is_interrupt_asserted()

    device.config_program_loop_count = 2

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

    # Interrupt triggered because we looped once
    assert await device.tqv.is_interrupt_asserted()

    await device.clear_interrupts_using32(
        clear_timer_interrupt = 0,
        clear_loop_interrupt = 1,
        clear_program_end_interrupt = 0,
        clear_program_counter_mid_interrupt = 0
    )

    assert not await device.tqv.is_interrupt_asserted()

# Timer interrupt test
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def interrupt_test5(dut):
    device = Device(dut)
    await device.init()

    program = [(0, 1), (0, 0), (1, 1), (1, 0)]
    
    device.config_program_end_index = (len(program) - 1) * 2
    device.config_timer_interrupt_en = 1
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 3

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

    assert await device.tqv.is_interrupt_asserted()


    # Interrupt triggered because we looped once
    assert await device.tqv.is_interrupt_asserted()

    await device.clear_interrupts(
        clear_timer_interrupt = 1,
        clear_loop_interrupt = 1,
        clear_program_end_interrupt = 1,
        clear_program_counter_mid_interrupt = 1
    )

    assert not await device.tqv.is_interrupt_asserted()
 
# Program counter mid interrupt test
@cocotb.test(timeout_time=2, timeout_unit="ms")
async def interrupt_test6(dut):
    device = Device(dut)
    await device.init()

    program_len = MAX_PROGRAM_LEN
    
    program = []

    random.seed(8888) 
    for _ in range(program_len):
        duration_selector = random.randint(0, 1)  # 1-bit selector: 0 or 1
        transmit_level = random.randint(0, 1)     # 1-bit transmit level: 0 or 1
        program.append((duration_selector, transmit_level))
    
    device.config_program_end_index = 63 * 2
    device.config_program_counter_mid_interrupt_en = 1
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 2
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 3

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

    # No interrupt triggered because program counter did not reach 64
    assert not await device.tqv.is_interrupt_asserted()

    device.config_program_end_index = 64 * 2

    await device.write_program(program)
    await device.test_expected_waveform_2bps(program)

    # Interrupt triggered because program counter reached 64
    assert await device.tqv.is_interrupt_asserted()

    await device.clear_interrupts_using32(
        clear_timer_interrupt = 0,
        clear_loop_interrupt = 0,
        clear_program_end_interrupt = 0,
        clear_program_counter_mid_interrupt = 1
    )

    assert not await device.tqv.is_interrupt_asserted()


# make sure we can switch different program & configs without residue

#assert await tqv.read_word_reg(8) == 0
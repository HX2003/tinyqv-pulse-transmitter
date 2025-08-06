# SPDX-FileCopyrightText: © 2025 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, FallingEdge, Edge

from tqv import TinyQV

# When submitting your design, change this to the peripheral number
# in peripherals.v.  e.g. if your design is i_user_peri05, set this to 5.
# The peripheral number is not used by the test harness.
PERIPHERAL_NUM = 0

class Device:
    def __init__(self, dut, tqv):
        self.dut = dut
        self.tqv = tqv
        self.reset_config()
         
    # only sets it, does not actually write to the device
    def reset_config(self):
        self.timer_interrupt_clear = 0
        self.loop_interrupt_clear = 0
        self.program_end_interrupt_clear = 0
        self.program_counter_128_interrupt_clear = 0
        self.config_start = 0
        self.config_timer_interrupt_en = 0
        self.config_loop_interrupt_en = 0
        self.config_program_end_interrupt_en = 0
        self.config_program_counter_128_interrupt_en = 0
        self.config_idle_level = 0
        self.config_invert_output = 0
        self.config_carrier_en = 0 
        self.config_carrier_duration = 0

        self.config_program_loop_count = 0
        self.config_program_loopback_index = 0
        self.config_program_end_index = 0 
        self.config_main_prescaler = 0
         
        self.config_main_low_duration_a = 0
        self.config_main_low_duration_b = 0
        self.config_main_high_duration_a = 0
        self.config_main_high_duration_b = 0

        
        self.config_auxillary_mask = 0
        self.config_auxillary_duration_a = 0
        self.config_auxillary_duration_b = 0
        self.config_auxillary_prescaler = 0

    async def write_reg_0(self):
        reg0 = self.timer_interrupt_clear \
            | (self.loop_interrupt_clear << 1) \
            | (self.program_end_interrupt_clear << 2) \
            | (self.program_counter_128_interrupt_clear << 3) \
            | (self.config_start << 7) \
            | (self.config_timer_interrupt_en << 8) \
            | (self.config_loop_interrupt_en << 9) \
            | (self.config_program_end_interrupt_en << 10) \
            | (self.config_program_counter_128_interrupt_en << 11) \
            | (self.config_idle_level << 13) \
            | (self.config_invert_output << 14) \
            | (self.config_carrier_en << 15) \
            | (self.config_carrier_duration << 16)
        
        await self.tqv.write_word_reg(0, reg0)

    async def write_reg_1(self):
        reg1 = self.config_program_loop_count \
            | (self.config_program_loopback_index << 8) \
            | (self.config_program_end_index << 16) \
            | (self.config_main_prescaler << 24)
        
        await self.tqv.write_word_reg(4, reg1)

    async def write_reg_2(self):
        reg2 = (self.config_main_high_duration_b << 24) | (self.config_main_high_duration_a << 16) | (self.config_main_low_duration_b << 8) | self.config_main_low_duration_a
        await self.tqv.write_word_reg(8, reg2)
    
    async def write_reg_3(self):
        reg3 = self.config_auxillary_mask \
            | (self.config_auxillary_duration_a << 8) \
            | (self.config_auxillary_duration_b << 16) \
            | (self.config_auxillary_prescaler << 24)
        
        await self.tqv.write_word_reg(12, reg3)

    async def write_reg_data(self, addr, data):
        await self.tqv.write_word_reg(addr, data)

    """ Start the program (also clears any interrupt) """
    async def start_program(self):
        self.timer_interrupt_clear = 1
        self.loop_interrupt_clear = 1
        self.program_end_interrupt_clear = 1
        self.program_counter_128_interrupt_clear = 1
        self.config_start = 1
        await self.write_reg_0()
        
        self.timer_interrupt_clear = 0
        self.loop_interrupt_clear = 0
        self.program_end_interrupt_clear = 0
        self.program_counter_128_interrupt_clear = 0
         
         
    
    # for a symbol tuple[int, int], 
    # the first value is the duration selector
    # the second value is the transmit level
    async def write_program(self, program: list[tuple[int, int]]):
        word = 0
        count = 0
        i = 0
        
        for symbol_duration_selector, symbol_transmit_level in program:
            symbol_data = (symbol_transmit_level << 1 ) | symbol_duration_selector

            word |= symbol_data << (i * 2)
            i += 1

            if i == 16:
                await self.tqv.write_reg_data(0b100000 | count, word)
                word = 0
                i = 0
                count += 4

        await self.write_reg_0()
        await self.write_reg_1()
        await self.write_reg_2()
        await self.write_reg_3()
        await self.write_reg_data(0b100000 | count, word)

        
    async def test_expected_waveform(self, program: list[tuple[int, int]]):
        # config_carrier_en must be 0, generation of expected_waveform not supported with this parameter
        assert not self.config_carrier_en

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
            expected_duration = ((duration + 1) << prescaler) + 1
            waveform.append((expected_duration, expected_output))

        # example waveform [(2, 1), (3, 0), (4, 1), (4, 1), (5, 0)] 

        # lets start the test
        # the program must be already configured
        await self.start_program()

        # Wait until valid output goes high
        while(self.dut.uo_out[3].value == 0):
            await ClockCycles(self.dut.clk, 1)

        #await RisingEdge(self.dut.test_harness.user_peripheral.valid_output)

        for w in waveform:
            duration = w[0]
            expected_level = w[1]

            for i in range(duration):
                assert self.dut.uo_out[2].value == expected_level
                await ClockCycles(self.dut.clk, 1)
    
@cocotb.test(timeout_time=10, timeout_unit="ms")
async def test_project(dut):
    dut._log.info("Start")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Interact with your design's registers through this TinyQV class.
    # This will allow the same test to be run when your design is integrated
    # with TinyQV - the implementation of this class will be replaces with a
    # different version that uses Risc-V instructions instead of the SPI test
    # harness interface to read and write the registers.
    tqv = TinyQV(dut, PERIPHERAL_NUM)

    # Reset
    await tqv.reset()

    dut._log.info("Test project behavior")

    device = Device(dut, tqv)

    # Basic test
    test_program_1 = [(0, 1), (0, 0), (1, 1), (1, 0)]
    device.reset_config()
    device.config_program_end_index = 4
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2
    await device.write_program(test_program_1)
    await device.test_expected_waveform(test_program_1)
    
    # Basic test
    test_program_2 = [(0, 1), (0, 0), (1, 1), (1, 1), (1, 0)]
    device.reset_config()
    device.config_program_end_index = 5
    device.config_main_low_duration_a = 13
    device.config_main_low_duration_b = 34
    device.config_main_high_duration_a = 10
    device.config_main_high_duration_b = 2
    await device.write_program(test_program_2)
    await device.test_expected_waveform(test_program_2)

    # Basic test with prescaler
    test_program_3 = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    device.reset_config()
    device.config_program_end_index = 5
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2
    device.config_main_prescaler = 1
    await device.write_program(test_program_3)
    await device.test_expected_waveform(test_program_3)

    # Basic test with bigger prescaler
    test_program_4 = [(1, 0), (0, 1), (0, 0), (1, 1), (1, 0)]
    device.reset_config()
    device.config_program_end_index = 5
    device.config_main_low_duration_a = 1
    device.config_main_low_duration_b = 3
    device.config_main_high_duration_a = 0
    device.config_main_high_duration_b = 2
    device.config_main_prescaler = 9
    await device.write_program(test_program_4)
    await device.test_expected_waveform(test_program_4)

    await ClockCycles(dut.clk, 100)
    #assert await tqv.read_byte_reg(0) == 0x78
    #assert await tqv.read_hword_reg(0) == 0x5678
    #assert await tqv.read_word_reg(0) == 0x82345678

    # Set an input value, in the example this will be added to the register value
    #dut.ui_in.value = 30

    # Wait for two clock cycles to see the output values, because ui_in is synchronized over two clocks,
    # and a further clock is required for the output to propagate.
    #await ClockCycles(dut.clk, 3)

    # The following assersion is just an example of how to check the output values.
    # Change it to match the actual expected output of your module:
    #assert dut.uo_out.value == 0x96

    # Input value should be read back from register 1
    #assert await tqv.read_byte_reg(4) == 30

    # Zero should be read back from register 2
    #assert await tqv.read_word_reg(8) == 0

    # A second write should work
    #await tqv.write_word_reg(0, 40)
    #assert dut.uo_out.value == 70

    """# Test the interrupt, generated when ui_in[6] goes high
    dut.ui_in[6].value = 1
    await ClockCycles(dut.clk, 1)
    dut.ui_in[6].value = 0

    # Interrupt asserted
    await ClockCycles(dut.clk, 3)
    assert await tqv.is_interrupt_asserted()

    # Interrupt doesn't clear
    await ClockCycles(dut.clk, 10)
    assert await tqv.is_interrupt_asserted()
    
    # Write bottom bit of address 8 high to clear
    await tqv.write_byte_reg(8, 1)
    assert not await tqv.is_interrupt_asserted()"""

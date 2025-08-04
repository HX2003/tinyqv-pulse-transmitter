/*
 * Copyright (c) 2025 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

// Change the name of this module to something that reflects its functionality and includes your name for uniqueness
// For example tqvp_yourname_spi for an SPI peripheral.
// Then edit tt_wrapper.v line 41 and change tqvp_example to your chosen module name.
module tqvp_hx2003_pulse_transmitter (
    input         clk,          // Clock - the TinyQV project clock is normally set to 64MHz.
    input         rst_n,        // Reset_n - low to reset.

    input  [7:0]  ui_in,        // The input PMOD, always available.  Note that ui_in[7] is normally used for UART RX.
                                // The inputs are synchronized to the clock, note this will introduce 2 cycles of delay on the inputs.

    output [7:0]  uo_out,       // The output PMOD.  Each wire is only connected if this peripheral is selected.
                                // Note that uo_out[0] is normally used for UART TX.

    input [5:0]   address,      // Address within this peripheral's address space
    input [31:0]  data_in,      // Data in to the peripheral, bottom 8, 16 or all 32 bits are valid on write.

    // Data read and write requests from the TinyQV core.
    input [1:0]   data_write_n, // 11 = no write, 00 = 8-bits, 01 = 16-bits, 10 = 32-bits
    input [1:0]   data_read_n,  // 11 = no read,  00 = 8-bits, 01 = 16-bits, 10 = 32-bits
    
    output [31:0] data_out,     // Data out from the peripheral, bottom 8, 16 or all 32 bits are valid on read when data_ready is high.
    output        data_ready,

    output        user_interrupt  // Dedicated interrupt request for this peripheral
);

    // The various configuration registers
    reg [31:0] reg_0;
    reg [31:0] reg_1;

    wire [15:0] config_carrier_start_count = reg_1[15:0];
    wire [7:0] byte2 = reg_1[23:16];
    wire [7:0] byte3 = reg_1[31:24]; 

    
    // Implement a 32-bit register writes
    always @(posedge clk) begin
        if (!rst_n) begin
            // Reset the registers to its defaults
            reg_0 <= 0;
            reg_1 <= 0;
        end else begin
            if (address == 6'd0) begin
                reg_0 <= data_in[31:0];
            end else if (address == 6'd1) begin
                reg_1 <= data_in[31:0];
            end
        end 
    end

    // Other stuff
    reg [15:0] carrier_counter;
    reg carrier_output;
    
    assign uo_out[6:0] = 0;
    assign uo_out[7] = carrier_output;

    always @(posedge clk) begin
        if (!rst_n) begin
            carrier_counter <= 0;
            carrier_output <= 0;
        end else begin
            carrier_counter <= carrier_counter - 1;
            if (carrier_counter == 16'b0) begin
                carrier_counter <= config_carrier_start_count;
                carrier_output <= ~carrier_output;
            end 
        end
    end
    
    // All addresses read 0.
    assign data_out = 32'b0;

    // All reads complete in 1 clock
    assign data_ready = 1;
    
    // User interrupt is generated on rising edge of ui_in[6], and cleared by writing a 1 to the low bit of address 8.
    reg example_interrupt;
    reg last_ui_in_6;

    always @(posedge clk) begin
        if (!rst_n) begin
            example_interrupt <= 0;
        end

        if (ui_in[6] && !last_ui_in_6) begin
            example_interrupt <= 1;
        end else if (address == 6'h8 && data_write_n != 2'b11 && data_in[0]) begin
            example_interrupt <= 0;
        end

        last_ui_in_6 <= ui_in[6];
    end

    assign user_interrupt = example_interrupt;

    // List all unused inputs to prevent warnings
    // data_read_n is unused as none of our behaviour depends on whether
    // registers are being read.
    wire _unused = &{data_read_n, 1'b0};

endmodule

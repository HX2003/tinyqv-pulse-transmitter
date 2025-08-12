/*
 * Copyright (c) 2025 HX2003
 * SPDX-License-Identifier: Apache-2.0
 */

// A latch array of 8 x 32 bits
//
// How to read:
// Reading is simple, data_out is basically muxed to the data_out of each 32 bit word, which is selectable via read_address
// 
// How to write,
// set write_address, and let it stabilise for 1-2 cycles
// thereafter, set write high for at least 1 cycle, then set it low thereafter

module latch_array (
    input wire [2:0] read_address,
    output wire [31:0] data_out,
    input wire write, // write must be high for at least 1 clock cycle, 1 clock cycle after the write_address is stable
    input wire [2:0] write_address,
    input wire [31:0] data_in
);
 
wire [31:0] data_array[7:0];
assign data_out = data_array[read_address];

genvar i;
generate
    for (i = 0; i < 8; i++) begin
        latch_word word(
            .data_in(data_in),
            .write_en_a(write),
            .write_en_b(write_address == i),
            .data_out(data_array[i])
        );
    end
endgenerate

endmodule

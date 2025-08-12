/*
 * Copyright (c) 2025 HX2003
 * SPDX-License-Identifier: Apache-2.0
 */

module latch_word (
    input wire [31:0] data_in,
    input wire write_en_a,
    input wire write_en_b,
    output wire [31:0] data_out
);

`ifdef COCOTB_SIM
    reg [31:0] data;

    wire write_en_safe = write_en_a & write_en_b;

    always @(write_en_safe or data_in)
    begin
        if (write_en_safe) begin
            data <= data_in;
        end
    end

    assign data_out = data;

`else
    wire [31:0] data;
    
    wire write_en_safe;
    // Latches are sensitive to glitches on its gate pin
    // For example, the write en may glitch for a moment when a comparision like write_address == j is being done
    
    // Specify that a AND gate be used to minimize this possibility
    (* keep *) sky130_fd_sc_hd__and2_1 safety_gate( .A(write_en_a), .B(write_en_b), .X(write_en_safe) );

    genvar i;
    generate
        for (i = 0; i < 32; i++) begin
            /* verilator lint_off PINMISSING */
            sky130_fd_sc_hd__dlxtp_1 p_latch_bit(.GATE(write_en_safe), .D(data_in[i]), .Q(data_out[i]));
        end
    endgenerate
`endif
 

endmodule

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

    // Fixed parameters
    localparam NUM_DATA_REG = 5; // NUM_DATA_REG must be <= 8

    // Calculated parameters
    localparam DATA_REG_ADDR_NUM_BITS = $clog2(NUM_DATA_REG);

    // The various configuration registers
    reg [31:0] reg_0;
    wire config_start = reg_0[0];
    wire config_loop = reg_0[1];
    wire config_idle_level = reg_0[2];
    wire config_invert_output = reg_0[3];
    wire config_carrier_en = reg_0[4];
    wire [1:0] config_interrupt = reg_0[6:5];
    wire [6:0] config_program_loopback_count = reg_0[13:7];
    wire [6:0] config_program_end_count = reg_0[20:14];
    wire [3:0] config_main_prescaler = reg_0[24:21];
    wire [3:0] config_auxillary_prescaler = reg_0[28:25];
    wire [2:0] unused_reg0 = reg_0[31:29];
    wire _unused_reg0 = &{unused_reg0, 1'b0};

    wire _config_invert_output_un = &{config_interrupt, 1'b0};
    reg [31:0] reg_1;
    wire [15:0] config_carrier_start_count = reg_1[15:0];
    wire [7:0] config_auxillary_mask = reg_1[23:16];
    wire [15:0] unused_reg1 = reg_1[31:24];
    wire _unused_reg1 = &{unused_reg1, 1'b0};

    reg [31:0] reg_2;
    wire [7:0] config_main_low_duration_a = reg_2[7:0];
    wire [7:0] config_main_low_duration_b = reg_2[15:8];
    wire [7:0] config_main_high_duration_a = reg_2[23:16];
    wire [7:0] config_main_high_duration_b = reg_2[31:24];

    reg [31:0] reg_3;
    wire [7:0] config_auxillary_low_duration_a = reg_3[7:0];
    wire [7:0] config_auxillary_low_duration_b = reg_3[15:8];
    wire [7:0] config_auxillary_high_duration_a = reg_3[23:16];
    wire [7:0] config_auxillary_high_duration_b = reg_3[31:24];

    // The rest of our code
    wire start_pulse;

    pulse_transmitter_rising_edge_detector config_start_rising_edge_detector(
        .clk(clk),
        .rst_n(rst_n),
        .sig_in(config_start),
        .pulse_out(start_pulse)
    );
    
    reg [31:0] DATA_MEM[NUM_DATA_REG - 1:0];

    // Implement a 32-bit register writes
    always @(posedge clk) begin
        if (!rst_n) begin
            // Reset the registers to its defaults
            reg_0 <= 0;
            reg_1 <= 0;
            reg_2 <= 0;
            reg_3 <= 0;
        end else begin
            if (data_write_n == 2'b10) begin
                if (address[5] == 1'b0) begin
                    case (address[1:0])
                        2'd0: reg_0 <= data_in[31:0];
                        2'd1: reg_1 <= data_in[31:0];
                        2'd2: reg_2 <= data_in[31:0];
                        2'd3: reg_3 <= data_in[31:0];
                    endcase
                end else begin
                    // map the lower bits to our DATA_MEM
                    DATA_MEM[address[(DATA_REG_ADDR_NUM_BITS - 1):0]] <= data_in[31:0];
                end
            end
        end 
    end

    // Other stuff
    reg [15:0] carrier_counter;
    reg carrier_output;
    
    assign uo_out[0] = 0;
    assign uo_out[1] = carrier_output;

    // Apply optional carrier
    wire modulated_output = config_carrier_en ? (transmit_level && carrier_output): transmit_level;

    // Insert idle level when not transmitting
    wire active_or_idle_output  = (valid_output) ? modulated_output : config_idle_level;
    
    // Apply optional inversion
    wire final_output = active_or_idle_output ^ config_invert_output;
    assign uo_out[2] = final_output;

    assign uo_out[7:3] = 0;

    always @(posedge clk) begin
        if (!rst_n || !config_start) begin
            carrier_counter <= 0;
            carrier_output <= 0;
        end else begin
            if (carrier_counter == 16'b0) begin
                carrier_counter <= config_carrier_start_count;
                carrier_output <= !carrier_output;
            end else begin
                carrier_counter <= carrier_counter - 1;
            end
        end
    end

    wire oneshot_timer_pulse;

    wire oneshot_timer_trigger;
    assign oneshot_timer_trigger = start_pulse_delayed_2 || oneshot_timer_pulse;
    reg [7:0] prefetched_timer_duration;
    reg [3:0] prefetched_prescaler;
    pulse_transmitter_countdown_timer countdown_timer(
        .clk(clk),
        .sys_rst_n(rst_n),
        .en(timer_enabled),
        .prescaler(prefetched_prescaler),
        .duration(prefetched_timer_duration),
        .pulse_out(oneshot_timer_pulse)
    );
    
    always @(posedge clk) begin
        if (!rst_n) begin
            transmit_level <= 0;
            prefetched_transmit_level <= 0;
        end else begin
            if(oneshot_timer_trigger) begin
                // save the transmit_level
                transmit_level <= prefetched_transmit_level;
            end
        end
    end

    reg [31:0] data_32;
    reg [1:0] symbol_data;

    // Combinatorics, multiplexer to obtain 2 bit symbol_data based on program_counter
    always @(*) begin
        data_32 = DATA_MEM[program_counter[6:4]];

        // Extract 2-bit chunk based on sel
        case (program_counter[3:0])
            4'd0:  symbol_data = data_32[1:0];
            4'd1:  symbol_data = data_32[3:2];
            4'd2:  symbol_data = data_32[5:4];
            4'd3:  symbol_data = data_32[7:6];
            4'd4:  symbol_data = data_32[9:8];
            4'd5:  symbol_data = data_32[11:10];
            4'd6:  symbol_data = data_32[13:12];
            4'd7:  symbol_data = data_32[15:14];
            4'd8:  symbol_data = data_32[17:16];
            4'd9:  symbol_data = data_32[19:18];
            4'd10: symbol_data = data_32[21:20];
            4'd11: symbol_data = data_32[23:22];
            4'd12: symbol_data = data_32[25:24];
            4'd13: symbol_data = data_32[27:26];
            4'd14: symbol_data = data_32[29:28];
            4'd15: symbol_data = data_32[31:30];
        endcase
    end
    
    wire use_auxillary = program_counter < 8 && config_auxillary_mask[program_counter[2:0]];

    reg prefetched_transmit_level;
    always @(posedge clk) begin
        if (!rst_n) begin
            prefetched_transmit_level <= 0;
            prefetched_timer_duration <= 0;
            prefetched_prescaler <= 0;
        end else begin
            if(program_counter_increment_trigger) begin
                // fetch the pulse information, and store it
                prefetched_transmit_level <= symbol_data[1];

                if (use_auxillary) begin
                    prefetched_prescaler <= config_auxillary_prescaler;
                    case (symbol_data)
                        2'd0: prefetched_timer_duration <= config_auxillary_low_duration_a;
                        2'd1: prefetched_timer_duration <= config_auxillary_low_duration_b;
                        2'd2: prefetched_timer_duration <= config_auxillary_high_duration_a;
                        2'd3: prefetched_timer_duration <= config_auxillary_high_duration_b;
                    endcase
                end else begin
                    prefetched_prescaler <= config_main_prescaler;
                    case (symbol_data)
                        2'd0: prefetched_timer_duration <= config_main_low_duration_a;
                        2'd1: prefetched_timer_duration <= config_main_low_duration_b;
                        2'd2: prefetched_timer_duration <= config_main_high_duration_a;
                        2'd3: prefetched_timer_duration <= config_main_high_duration_b;
                    endcase
                end
            end
        end
    end
 
    reg transmit_level;

    reg valid_output;

    // The program counter should increment:
    // once for start_pulse (we fetch the current symbol and increment program_counter)
    // once for start_pulse_delayed_1 (we prefetch the next symbol and increment program_counter)
    // every time we trigger the timer (note: program counter is incremented before timer has elapsed, because we want to prefetch)
    wire program_counter_increment_trigger = start_pulse || oneshot_timer_trigger;

    reg program_counter_reached_end;
    reg start_pulse_delayed_1;
    reg start_pulse_delayed_2;
    reg timer_enabled;

    reg [6:0] program_counter;
    always @(posedge clk) begin
        if (!rst_n || !config_start) begin
            timer_enabled <= 0;
            program_counter_reached_end <= 0;
            program_counter <= 0;
            valid_output <= 0;
            start_pulse_delayed_1 <= 0;
            start_pulse_delayed_2 <= 0;
        end else begin
            start_pulse_delayed_1 <= start_pulse;
            start_pulse_delayed_2 <= start_pulse_delayed_1;

            if (start_pulse_delayed_1) begin
                timer_enabled <= 1;
            end

            if (start_pulse_delayed_2) begin
                // It takes 1 cycle to fetch the pulse information,
                // and another 1 cycle for the timer to start
                // so the initial output is not valid until 2 cycle later 
                valid_output <= 1;
            end

            if (program_counter_increment_trigger) begin
                if (program_counter == config_program_end_count) begin
                    if(config_loop) begin
                        // Set the program counter
                        program_counter <= config_program_loopback_count;
                    end else begin
                        // Set program_counter_reached_end, but do not disable output yet
                        program_counter_reached_end <= 1;
                    end
                     
                end else begin
                    program_counter <= program_counter + 1;
                end
            end

            if (oneshot_timer_trigger && program_counter_reached_end) begin
                valid_output <= 0;
            end
        end
    end

    // 
    always @(posedge clk) begin
        if (!rst_n) begin
        end else begin
            
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
    wire _unused1 = &{data_read_n, 1'b0};
    wire _unused2 = &{ui_in, 1'b0};

endmodule

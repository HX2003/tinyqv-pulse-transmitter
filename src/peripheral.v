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
    localparam NUM_DATA_REG = 8; // NUM_DATA_REG must be <= 8

    // Calculated parameters
    localparam DATA_REG_ADDR_NUM_BITS = $clog2(NUM_DATA_REG);

    // The various configuration registers
    reg [31:0] reg_0;
    // First 8 bits (Interrupt flags and config start)
    wire [3:0] interrupt_event_flag = {
        1'b0, // bit 3 (program_counter_64_interrupt)
        1'b0, // bit 2 (program_end_interrupt)
        1'b0, // bit 1 (loop_interrupt)
        timer_pulse_out // bit 0 (timer_interrupt)
    };
    wire _unused_reg_0_a = &{reg_0[6:4], 1'b0};
    wire config_start = reg_0[7];
    // Next 8 bits (Interrupt enable and other configs)
    wire config_timer_interrupt_en = reg_0[8];
    wire config_loop_interrupt_en = reg_0[9];
    wire config_program_end_interrupt_en = reg_0[10];
    wire config_program_counter_64_interrupt_en = reg_0[11];
    wire config_loop_forever = reg_0[12];
    wire config_idle_level = reg_0[13];
    wire config_invert_output = reg_0[14];
    wire config_carrier_en = reg_0[15];
    // Next 16 bits (Carrier duration)
    wire [15:0] config_carrier_duration = reg_0[31:16];

    reg [31:0] reg_1;
    wire [7:0] config_program_loop_count = reg_1[7:0];
    wire [6:0] config_program_loopback_index = reg_1[14:8];
    wire _unused_reg_1_a = &{reg_1[15], 1'b0};
    wire [6:0] config_program_end_index = reg_1[22:16];
    wire _unused_reg_1_b = &{reg_1[23], 1'b0};
    wire [3:0] config_main_prescaler = reg_1[27:24];
    wire _unused_reg_1_c = &{reg_0[31:28], 1'b0};

    reg [31:0] reg_2;
    wire [7:0] config_main_low_duration_a = reg_2[7:0];
    wire [7:0] config_main_low_duration_b = reg_2[15:8];
    wire [7:0] config_main_high_duration_a = reg_2[23:16];
    wire [7:0] config_main_high_duration_b = reg_2[31:24];

    reg [31:0] reg_3;
    wire [7:0] config_auxillary_mask = reg_3[7:0];
    wire [7:0] config_auxillary_duration_a = reg_3[15:8];
    wire [7:0] config_auxillary_duration_b = reg_3[23:16];
    wire [3:0] config_auxillary_prescaler = reg_3[27:24];
    wire _unused_reg_3_a = &{reg_3[31:28], 1'b0};

    // The rest of our code
    wire start_pulse;

    pulse_transmitter_rising_edge_detector config_start_rising_edge_detector(
        .clk(clk),
        .rst_n(rst_n),
        .sig_in(config_start),
        .pulse_out(start_pulse)
    );
    
    reg [31:0] DATA_MEM[(NUM_DATA_REG - 1):0];

    // Implement a 32-bit register writes for the config and data (aligned to 32 bits)
    always @(posedge clk) begin
        if (!rst_n) begin
            // Reset the registers to its defaults
            reg_0 <= 0;
            reg_1 <= 0;
            reg_2 <= 0;
            reg_3 <= 0;
        end else begin
            if (data_write_n == 2'b10) begin
                // 32 bit writes (aligned to 32 bits)
                if (address[5] == 1'b0) begin
                    // Addresses 0, 4, 8, 12 (does not handle not aligned writes)
                    case (address[3:2])
                        2'd0: begin
                            // reg_0[3:0] stores the interrupt values
                            // BITS 4 to 6 are not used here
                            reg_0[3:0] <= (reg_0[3:0] & ~data_in[3:0]) | interrupt_event_flag;
                            reg_0[31:7] <= data_in[31:7];
                        end
                        2'd1: reg_1 <= data_in[31:0];
                        2'd2: reg_2 <= data_in[31:0];
                        2'd3: reg_3 <= data_in[31:0];
                    endcase
                end else begin
                    // map the address to our DATA_MEM
                    // 0b100000 -> DATA_MEM index 0
                    // 0b100100 -> DATA_MEM index 1
                    // 0b101000 -> DATA_MEM index 2
                    DATA_MEM[address[(DATA_REG_ADDR_NUM_BITS - 1 + 2):2]] <= data_in[31:0];
                end
            end else if (data_write_n == 2'b00) begin
                // 8 bit writes
                if (address == 0) begin
                    // reg_0[3:0] stores the interrupt values
                    // BITS 4 to 6 are not used here
                    reg_0[3:0] <= (reg_0[3:0] & ~data_in[3:0]) | interrupt_event_flag;
                    reg_0[7] <= data_in[7]; 
                end
            end else begin
                // reg_0[3:0] stores the interrupt values
                reg_0[3:0] <= reg_0[3:0] | interrupt_event_flag;
            end
        end 
    end
 
    // Interrupt
    assign user_interrupt = interrupt_event_flag > 0;

    // Apply optional carrier
    wire modulated_output = config_carrier_en ? (transmit_level && carrier_out): transmit_level;

    // Insert idle level when not transmitting
    wire active_or_idle_output = (valid_output) ? modulated_output : config_idle_level;
    
    // Apply optional inversion
    wire final_output = active_or_idle_output ^ config_invert_output;

    reg [15:0] carrier_counter;
    reg carrier_out;
    wire carrier_pulse_out;
    pulse_transmitter_rising_edge_detector carrier_out_rising_edge_detector(
        .clk(clk),
        .rst_n(rst_n),
        .sig_in(carrier_out),
        .pulse_out(carrier_pulse_out)
    );

    always @(posedge clk) begin
        if (!rst_n || !config_start) begin
            carrier_counter <= 0;
            carrier_out <= 0;
        end else begin
            if (carrier_counter == 16'b0) begin
                carrier_counter <= config_carrier_duration;
                carrier_out <= !carrier_out;
            end else begin
                carrier_counter <= carrier_counter - 1;
            end
        end
    end

    wire timer_pulse_out;

    wire timer_trigger = start_pulse_delayed_2 || timer_pulse_out;
    reg [7:0] prefetched_duration;
    reg [3:0] prefetched_prescaler;
    pulse_transmitter_countdown_timer countdown_timer(
        .clk(clk),
        .sys_rst_n(rst_n),
        .en(timer_enabled),
        .prescaler(prefetched_prescaler),
        .duration(prefetched_duration),
        .pulse_out(timer_pulse_out)
    );

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
            prefetched_duration <= 0;
            prefetched_prescaler <= 0;
        end else begin
            if(program_counter_increment_trigger) begin
                // fetch the pulse information, and store it
                prefetched_transmit_level <= symbol_data[1];

                if (use_auxillary) begin
                    prefetched_prescaler <= config_auxillary_prescaler;
                    if(symbol_data[0] == 1'b0) begin
                        prefetched_duration <= config_auxillary_duration_a;
                        prefetched_duration <= config_auxillary_duration_b;
                    end
                end else begin
                    prefetched_prescaler <= config_main_prescaler;
                    case (symbol_data)
                        2'd0: prefetched_duration <= config_main_low_duration_a;
                        2'd1: prefetched_duration <= config_main_low_duration_b;
                        2'd2: prefetched_duration <= config_main_high_duration_a;
                        2'd3: prefetched_duration <= config_main_high_duration_b;
                    endcase
                end
            end
        end
    end
 
    reg transmit_level;
    always @(posedge clk) begin
        if (!rst_n) begin
            transmit_level <= 0;
        end else begin
            if(timer_trigger) begin
                // save the transmit_level
                transmit_level <= prefetched_transmit_level;
            end
        end
    end

    reg valid_output;

    // The program counter should increment:
    // once for start_pulse (we fetch the current symbol and increment program_counter)
    // every time we trigger the timer (note: program counter is incremented before timer has elapsed, because we want to prefetch)
    wire program_counter_increment_trigger = start_pulse || timer_trigger;
    
    reg [6:0] program_counter;
    reg [8:0] program_loop_counter; // add 1 more bit for the rollover detector
    reg program_end_of_file;
    reg program_end_of_file_delayed_1;
    reg start_pulse_delayed_1;
    reg start_pulse_delayed_2;
    reg timer_enabled;
     
    always @(posedge clk) begin
        if (!rst_n || !config_start) begin
            program_loop_counter <= {1'b0, config_program_loop_count} - 1;
            timer_enabled <= 0;
            program_end_of_file <= 0;
            program_end_of_file_delayed_1 <= 0;
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
                if (program_counter == config_program_end_index) begin
                    if (!config_loop_forever && (program_loop_counter[8] == 1'b1)) begin
                        // Set program_end_of_file
                        // But do not disable output yet, as the preloaded values are not yet flushed out
                        program_end_of_file <= 1;
                    end else begin
                        // We want to loop, set the program counter
                        program_counter <= config_program_loopback_index;
                        program_loop_counter <= program_loop_counter - 1;
                    end
                end else begin
                    program_counter <= program_counter + 1;
                end
            end

            if (timer_trigger) begin
                program_end_of_file_delayed_1 <= program_end_of_file;
            end

            if (timer_trigger && program_end_of_file_delayed_1) begin
                valid_output <= 0;
            end

            
        end
    end

    // Pin outputs
    assign uo_out[0] = 0;
    assign uo_out[1] = carrier_out;
    assign uo_out[2] = final_output;
    assign uo_out[3] = valid_output;
    assign uo_out[7:4] = 0;

    // All addresses read 0.
    assign data_out = 32'b0;

    // All reads complete in 1 clock
    assign data_ready = 1;
 
    // List all unused inputs to prevent warnings
    // data_read_n is unused as none of our behaviour depends on whether
    // registers are being read.
    wire _unused1 = &{data_read_n, 1'b0};
    wire _unused2 = &{ui_in, 1'b0};

endmodule

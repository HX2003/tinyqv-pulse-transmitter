// This module implements a repeating countdown timer.
// When en is 1, it generates a 1-cycle pulse after (duration << prescaler) + 2 number of clock cycles
// 
// When prescaler = 0, duration is not affected
// When prescaler = 1, duration is multiplied by 2
// When prescaler = 2, duration is multiplied by 4
// and so on...
//
// On pulse_out, the next counter value is loaded base on prescaler and duration parameters
//
// Note that prescaler and duration must be provided 1 cycle before en is 1

module pulse_transmitter_countdown_timer #(
    parameter PRESCALER_WIDTH = 15,
    parameter TIMER_WIDTH = 8
) (
    input wire clk,
    input wire sys_rst_n,
    input wire en,
    input wire [($clog2(PRESCALER_WIDTH + 1) - 1):0] prescaler,
    input wire [(TIMER_WIDTH - 1):0] duration,
    output wire pulse_out
);
    // When prescaler width = 15, and timer width = 8,
    // 0b10000000 << 15, which gives us 23 bits
    // Add 1 more bit for the rollover detector to give us 24 bits
    localparam COUNTER_WIDTH = PRESCALER_WIDTH + TIMER_WIDTH + 1;

    pulse_transmitter_rising_edge_detector out_rising_edge_detector(
        .clk(clk),
        .rst_n(sys_rst_n),
        .sig_in(out),
        .pulse_out(pulse_out)
    );

    wire [(PRESCALER_WIDTH ):0] prescaler_start_count = {1'b0, {(PRESCALER_WIDTH - 1){1'b0}} << prescaler};
    wire [(TIMER_WIDTH):0] start_count = {1'b0, duration};

    reg out;
    reg [(PRESCALER_WIDTH):0] prescaler_counter; // Add 1 more bit for the rollover detector
    reg [(TIMER_WIDTH):0] counter; // Add 1 more bit for the rollover detector
 
    always @(posedge clk) begin
        if (!sys_rst_n || !en) begin
            counter <= start_count;
            prescaler_counter <= prescaler_start_count;
            out <= 1'b0;
        end else begin 
            if(prescaler_counter[PRESCALER_WIDTH] == 1'b1) begin
                if(counter[TIMER_WIDTH] == 1'b1) begin
                    counter <= start_count;
                    out <= 1'b1;
                end else begin
                    counter <= counter - 1;
                    out <= 1'b0;
                end
            end else begin
                prescaler_counter <= prescaler_counter - 1;
            end
        end
    end

endmodule
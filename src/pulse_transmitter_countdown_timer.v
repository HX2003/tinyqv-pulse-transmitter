// This module implements a one-shot countdown timer.
// After once tim_trig goes low, it generates a 1-cycle pulse
// after (duration << prescaler) number of clock cycles
//
// When prescaler = 0, duration is not affected
// When prescaler = 1, duration is multiplied by 2
// When prescaler = 2, duration is multiplied by 4
// and so on...

module pulse_transmitter_countdown_timer #(
    parameter PRESCALER_WIDTH = 15,
    parameter TIMER_WIDTH = 8
) (
    input wire clk,
    input wire sys_rst_n,
    input wire tim_trig,
    input wire [($clog2(PRESCALER_WIDTH + 1) - 1):0] prescaler,
    input wire [(TIMER_WIDTH - 1):0] duration,
    output wire pulse_out
);
    // When prescaler width = 15, and timer width = 8,
    // 0b10000000 << 15, which gives us 23 bits
    // Add 1 more bit for the rollover detector to give us 24 bits
    localparam COUNTER_WIDTH = PRESCALER_WIDTH + TIMER_WIDTH + 1;
    
    wire tim_trig_pulse = tim_trig;
    //wire tim_trig_pulse;
    //pulse_transmitter_rising_edge_detector tim_trig_rising_edge_detector(
    //    .clk(clk),
    //    .rst_n(sys_rst_n),
    //    .sig_in(tim_trig),
    //    .pulse_out(tim_trig_pulse)
    //);

    pulse_transmitter_rising_edge_detector out_rising_edge_detector(
        .clk(clk),
        .rst_n(sys_rst_n),
        .sig_in(out),
        .pulse_out(pulse_out)
    );

    reg out;
    reg started;
    reg [(COUNTER_WIDTH - 1):0] counter;

    always @(posedge clk) begin
        if (!sys_rst_n) begin
            counter <= 0;
            started <= 1'b0;
            out <= 1'b0;
        end else begin 
            if (tim_trig_pulse) begin
                counter <= {1'b0, duration << prescaler} - 1;
                if (tim_trig_pulse) begin
                    out <= 1'b0;
                    started <= 1'b1;
                end
            end else if(counter[COUNTER_WIDTH - 1] == 1'b1) begin
                started <= 1'b0;
                out <= 1'b1;
            end else if(started) begin
                counter <= counter - 1;
            end
        end
    end

endmodule
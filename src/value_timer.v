// This module implements a one-shot countdown timer that generates a 1-cycle pulse
// after the duration specified

module value_timer #(
    parameter TIMER_WIDTH = 8
) (
    input wire clk,
    input wire sys_rst_n,
    input wire tim_trig,
    input wire [(TIMER_WIDTH - 1):0] duration,
    output wire pulse_out
);

    wire tim_trig_pulse;
    rising_edge_detector tim_trig_rising_edge_detector(
        .clk(clk),
        .rstb(sys_rst_n),
        .ena(1'b1),
        .data(tim_trig),
        .pos_edge(tim_trig_pulse)
    );

    rising_edge_detector out_rising_edge_detector(
        .clk(clk),
        .rstb(sys_rst_n),
        .ena(1'b1),
        .data(out),
        .pos_edge(pulse_out)
    );

    reg out;
    reg started;
    reg [TIMER_WIDTH:0] counter; // give an extra bit for the rollover

    always @(posedge clk) begin
        if (!sys_rst_n) begin
            counter <= 0;
            started <= 1'b0;
            out <= 1'b0;
        end else begin 
            if (tim_trig_pulse) begin
                counter <= {1'b0, duration} - 1;
                if (tim_trig_pulse) begin
                    out <= 1'b0;
                    started <= 1'b1;
                end
            end else if(counter[TIMER_WIDTH] == 1'b1) begin
                started <= 1'b0;
                out <= 1'b1;
            end else if(started) begin
                counter <= counter - 1;
            end
        end
    end

endmodule
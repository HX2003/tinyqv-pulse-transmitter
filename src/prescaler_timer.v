// This module implements a countdown timer that generates a 1-cycle pulse at periodic intervals,
// the interval is based on the prescaler value
//
// For example
// prescaler = 0, the output is 1
// prescaler = 1, the output is 0 for 1 clk cycle, and 1 for 1 clk cycle
// prescaler = 2, the output is 0 for 2 clk cycles, and 1 for 2 clk cycles
// prescaler = 3, the output is 0 for 4 clk cycles, and 1 for 4 clk cycles
// and so on ...
//
// when tim_rst is 1, the output is always 0

module prescaler_timer #(
    parameter PRESCALER_NUM_BITS = 4
) (
    input wire clk,
    input wire sys_rst_n,
    input wire tim_rst,
    input wire [(PRESCALER_NUM_BITS - 1):0] prescaler,
    output reg out
);

    localparam COUNTER_WIDTH = 2 ** PRESCALER_NUM_BITS;

    wire [(COUNTER_WIDTH - 1):0] start_count = (1 << (prescaler - 1)) - 1;
    reg [COUNTER_WIDTH:0] counter; // give an extra bit for the rollover

    always @(posedge clk) begin
        if (!sys_rst_n) begin
            counter <= 0;
            out <= 1'b0;
        end else begin
            if (!tim_rst && prescaler == 'b0) begin
                out <= 1'b1;
            end else if (tim_rst || (counter[COUNTER_WIDTH] == 1'b1)) begin
                counter <= {1'b0, start_count} - 1;
                if (tim_rst) begin
                    out <= 1'b0;
                end else begin
                    out <= !out;
                end
            end else begin
                counter <= counter - 1;
            end
        end
    end

endmodule
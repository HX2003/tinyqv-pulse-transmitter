module prescaler_timer #(
    parameter PRESCALER_NUM_BITS = 4
) (
    input wire clk,
    input wire sys_rst_n,
    input wire tim_rst_n,
    input wire [(PRESCALER_NUM_BITS - 1):0] prescaler,
    output reg out
);

    localparam COUNTER_WIDTH = 2 ** PRESCALER_NUM_BITS;

    wire [(COUNTER_WIDTH - 1):0] start_count = (1 << prescaler) - 1;
    reg [COUNTER_WIDTH:0] counter; // give an extra bit for the rollover

    always @(posedge clk) begin
        if (!sys_rst_n || tim_rst_n || (counter[COUNTER_WIDTH] == 1'b1)) begin
            counter <= {1'b0, start_count} - 1;
            if (!sys_rst_n || tim_rst_n) begin
                out <= 1'b0;
            end else begin
                out <= !out;
            end
        end else begin
            counter <= counter - 1;
        end
    end 

endmodule
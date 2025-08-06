module pulse_transmitter_delay_1 (
    input  wire clk,
    input  wire sys_rst_n,
    input  wire sig_in,
    output reg  sig_delayed_1_out
);

    always @(posedge clk) begin
        if (!sys_rst_n) begin
            sig_delayed_1_out <= 1'b0;
        end else begin
            sig_delayed_1_out <= sig_in;
        end
    end

endmodule
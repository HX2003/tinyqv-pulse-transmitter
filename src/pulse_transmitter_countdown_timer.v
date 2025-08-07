// This module implements a repeating countdown timer.
// When en is 1, it generates a 1-cycle pulse after ((duration + 1) << prescaler) + 1) number of clock cycles
// 
// When prescaler = 0, the total duration is (duration + 1) * 1 + 1 = duration + 2
// When prescaler = 1, the total duration is (duration + 1) * 2 + 1
// When prescaler = 2, the total duration is (duration + 1) * 4 + 1
// and so on...
//
// On pulse_out, the next counter value is loaded base on prescaler and duration parameters
//
// Note that prescaler and duration must be provided 1 cycle before en is 1

module pulse_transmitter_countdown_timer #(
    parameter PRESCALER_WIDTH = 16,
    parameter TIMER_WIDTH = 8
) (
    input wire clk,
    input wire sys_rst_n,
    input wire en,
    input wire [($clog2(PRESCALER_WIDTH) - 1):0] prescaler,
    input wire [(TIMER_WIDTH - 1):0] duration,
    output wire request_data,
    output wire pulse_out
);  
    reg out;
    
    // shifting the duration like this is the simplest, but takes a little more logic gates
    // wire [(COUNTER_WIDTH - 1):0] counter_start = {1'b0, {{PRESCALER_WIDTH{1'b0}}, duration} << prescaler};

    pulse_transmitter_rising_edge_detector out_rising_edge_detector(
        .clk(clk),
        .rst_n(sys_rst_n),
        .sig_in(out),
        .pulse_out(pulse_out)
    );

    // Request data when the counter reaches 0, provided the timer is enabled
    assign request_data = en && (counter == 0) && (prescaler_counter[PRESCALER_WIDTH] == 1'b1);

    reg [(PRESCALER_WIDTH):0] prescaler_counter;
    // example values of prescaler_compare
    // prescaler = 0, prescaler_compare = 0b0000
    // prescaler = 1, prescaler_compare = 0b0001
    // prescaler = 2, prescaler_compare = 0b0011
    // prescaler = 3, prescaler_compare = 0b0111
    //wire [(PRESCALER_WIDTH):0] prescaler_full = {{ };

    wire [PRESCALER_WIDTH:0] prescaler_start_count = {1'b0, {{(PRESCALER_WIDTH - 1){1'b0}}, 1'b1} << prescaler} - 2;
    
    reg [TIMER_WIDTH:0] counter; // extra bit for rollover
    wire [TIMER_WIDTH:0] start_count = {1'b0, duration};  // extra bit for rollover

    always @(posedge clk) begin
        if (!sys_rst_n || !en) begin
            counter <= start_count;
            prescaler_counter <= prescaler_start_count;
            out <= 1'b0;
        end else begin
            if (prescaler_counter[PRESCALER_WIDTH] == 1'b1) begin
                prescaler_counter <= prescaler_start_count;
                if (counter[TIMER_WIDTH] == 1'b1) begin
                    counter <= start_count;
                    out <= 1'b1;
                end else begin
                    out <= 1'b0;
                    counter <= counter - 1;
                end
            end else begin
                out <= 1'b0;
                prescaler_counter <= prescaler_counter - 1;
            end
        end
    end

/*
if (counter[TIMER_WIDTH] == 1'b1) begin
                prescaler_counter <= prescaler_start_count;
                counter <= start_count;
                out <= 1'b1;
            end else begin
                out <= 1'b0;
                if (prescaler_counter[PRESCALER_WIDTH] == 1'b1) begin
                    prescaler_counter <= prescaler_start_count;
                    counter <= counter - 1;
                end else begin
                    prescaler_counter <= prescaler_counter - 1;
                end
            end
*/
    /* WORKING
    reg out;
    
    // shifting the duration like this takes a little more logic gates
    // wire [(COUNTER_WIDTH - 1):0] counter_start = {1'b0, {{PRESCALER_WIDTH{1'b0}}, duration} << prescaler};

    pulse_transmitter_rising_edge_detector out_rising_edge_detector(
        .clk(clk),
        .rst_n(sys_rst_n),
        .sig_in(out),
        .pulse_out(pulse_out)
    );

    // Request data when the counter reaches 1, provided the timer is enabled
    assign request_data = en && (counter == 1);

    reg [(PRESCALER_WIDTH):0] prescaler_counter;
    // example values of prescaler_compare
    // prescaler = 0, prescaler_compare = 0b0000
    // prescaler = 1, prescaler_compare = 0b0001
    // prescaler = 2, prescaler_compare = 0b0011
    // prescaler = 3, prescaler_compare = 0b0111
    //wire [(PRESCALER_WIDTH):0] prescaler_full = {{ };

    wire [(PRESCALER_WIDTH):0] prescaler_start_count = {1'b0, {{(PRESCALER_WIDTH - 1){1'b0}}, 1'b1} << prescaler} - 2;
    
    reg [(TIMER_WIDTH - 1):0] counter;
    wire [(TIMER_WIDTH - 1):0] start_count = duration;

    always @(posedge clk) begin
        if (!sys_rst_n || !en) begin
            counter <= start_count;
            prescaler_counter <= prescaler_start_count;
            out <= 1'b0;
        end else begin 
            if (counter == 0) begin
                prescaler_counter <= prescaler_start_count;
                counter <= start_count;
                out <= 1'b1;
            end else begin
                out <= 1'b0;
                if (prescaler_counter[PRESCALER_WIDTH] == 1'b1) begin
                    prescaler_counter <= prescaler_start_count;
                    counter <= counter - 1;
                end else begin
                    prescaler_counter <= prescaler_counter - 1;
                end
            end
        end
    end
    */
    /*
      reg [(PRESCALER_WIDTH):0] prescaler_counter;
    // example values of prescaler_compare
    // prescaler = 0, prescaler_compare = 0b0000
    // prescaler = 1, prescaler_compare = 0b0001
    // prescaler = 2, prescaler_compare = 0b0011
    // prescaler = 3, prescaler_compare = 0b0111
    //wire [(PRESCALER_WIDTH):0] prescaler_full = {{ };

    wire [(PRESCALER_WIDTH):0] prescaler_start_count = {1'b0, {{(PRESCALER_WIDTH - 1){1'b0}}, 1'b1} << prescaler} - 2;
    
    reg [(TIMER_WIDTH):0] counter; // Add 1 more bit for the rollover detector
    wire [(TIMER_WIDTH):0] start_count = {1'b0, duration};
    wire counter_overflow = counter[TIMER_WIDTH] == 1'b1;

    // Request data when the counter_overflow, provided the timer is enabled
    assign request_data = en && counter_overflow;
    
    // Out is raised 1 cycle after 1 request_data is high, since it goes through a flipflop 
    reg out;
    
    always @(posedge clk) begin
        if (!sys_rst_n || !en) begin
            counter <= start_count;
            prescaler_counter <= prescaler_start_count;
            out <= 1'b0;
        end else begin 
            if (counter_overflow) begin
                prescaler_counter <= prescaler_start_count;
                counter <= start_count;
                out <= 1'b1;
            end else begin
                out <= 1'b0;
                if (prescaler_counter[PRESCALER_WIDTH] == 1'b1) begin
                    prescaler_counter <= prescaler_start_count;
                    counter <= counter - 1;
                end else begin
                    prescaler_counter <= prescaler_counter - 1;
                end
            end
        end
    end=
*/

    /*
    
    always @(posedge clk) begin
        if (!sys_rst_n || !en) begin
            counter <= start_count;
            prescaler_counter <= prescaler_start_count;
            out <= 1'b0;
        end else begin 
            if (prescaler_counter[PRESCALER_WIDTH] == 1'b1) begin
                prescaler_counter <= prescaler_start_count;
                if (counter[TIMER_WIDTH] == 1'b1) begin
                    counter <= start_count;
                    out <= 1'b1;
                end else begin
                    counter <= counter - 1;
                    out <= 1'b0;
                end
            end else begin
                prescaler_counter <= prescaler_counter - 1;
                out <= 1'b0;
            end
        end
    end*/
    /*wire [(TIMER_WIDTH + PRESCALER_WIDTH):0] counter_start = {1'b0, {{PRESCALER_WIDTH{1'b0}}, duration} << prescaler};
    reg [(TIMER_WIDTH + PRESCALER_WIDTH):0] counter; // Add 1 more bit for the rollover detector

    always @(posedge clk) begin
        if (!sys_rst_n || !en) begin
            counter <= counter_start;
            out <= 1'b0;
        end else begin 
            if(counter[TIMER_WIDTH + PRESCALER_WIDTH] == 1'b1) begin
                counter <= counter_start;
                out <= 1'b1;
            end else begin
                counter <= counter - 1;
                out <= 1'b0;
            end
        end
    end*/

    /*
    reg [(PRESCALER_WIDTH - 1):0] prescaler_counter;
    // example values of prescaler_compare
    // prescaler = 0, prescaler_compare = 0b0000
    // prescaler = 1, prescaler_compare = 0b0001
    // prescaler = 2, prescaler_compare = 0b0011
    // prescaler = 3, prescaler_compare = 0b0111
    wire [(PRESCALER_WIDTH - 1):0] prescaler_compare = ({{(PRESCALER_WIDTH - 1){1'b0}}, 1'b1} << prescaler) - 1;
    
    reg [(TIMER_WIDTH):0] counter; // Add 1 more bit for the rollover detector
    wire [(TIMER_WIDTH):0] start_count = {1'b0, duration};

    always @(posedge clk) begin
        if (!sys_rst_n || !en) begin
            counter <= start_count;
            prescaler_counter <= 0;
            out <= 1'b0;
        end else begin 
            if((prescaler_counter & prescaler_compare) == 0) begin
                if(counter[TIMER_WIDTH] == 1'b1) begin
                    prescaler_counter <= 0;
                    counter <= start_count;
                    out <= 1'b1;
                end else begin
                    prescaler_counter <= prescaler_counter - 1;
                    counter <= counter - 1;
                    out <= 1'b0;
                end
            end else begin
                prescaler_counter <= prescaler_counter - 1;
            end
        end
    end*/

endmodule

module delay_line #(
    parameter DATA_WIDTH = 12,
    parameter DATA_DELAY = 12
)(
    input  wire                              clk,
    input  wire                              clr,
    input  wire                              en,
    input  wire signed [DATA_WIDTH-1:0]      data_in,
    output wire [DATA_DELAY*DATA_WIDTH-1:0]  taps_bus,
    output reg                               line_full
);
    localparam CNT_W = $clog2(DATA_DELAY + 1);
    reg signed [DATA_WIDTH-1:0] shift_reg [0:DATA_DELAY-1];
    reg [CNT_W-1:0] fill_cnt;
    genvar i;

    always @(posedge clk or posedge clr) begin
        if (clr) shift_reg[0] <= 0;
        else if (en) shift_reg[0] <= data_in;
    end

    generate
        for (i = 1; i < DATA_DELAY; i = i + 1) begin : gen_shift
            always @(posedge clk or posedge clr) begin
                if (clr)     shift_reg[i] <= 0;
                else if (en) shift_reg[i] <= shift_reg[i-1];
            end
        end
    endgenerate

    always @(posedge clk or posedge clr) begin
        if (clr) begin
            fill_cnt  <= 0;
            line_full <= 1'b0;
        end else if (en && !line_full) begin
            if (fill_cnt == DATA_DELAY)
                line_full <= 1'b1;
            else
                fill_cnt <= fill_cnt + 1;
        end
    end

    generate
        for (i = 0; i < DATA_DELAY; i = i + 1) begin : gen_flat
            assign taps_bus[(i+1)*DATA_WIDTH-1 : i*DATA_WIDTH] = shift_reg[i];
        end
    endgenerate

endmodule
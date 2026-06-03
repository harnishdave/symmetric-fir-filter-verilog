
module pre_adder #(
    parameter COEFF_NUM    = 6,
    parameter DATA_WIDTH   = 12,
    parameter DATA_DELAY   = 12,
    parameter STAGE1_WIDTH = DATA_WIDTH + 1
)(
    input  wire                               clk,
    input  wire                               clr,
    input  wire                               en,
    input  wire [DATA_DELAY*DATA_WIDTH-1:0]   taps_bus,
    output reg  [COEFF_NUM*STAGE1_WIDTH-1:0]  presums_bus,
    output reg                                valid_out
);
    genvar j;

    generate
        for (j = 0; j < COEFF_NUM; j = j + 1) begin : gen_preadd
            wire signed [DATA_WIDTH-1:0] tap_lo = taps_bus[(j+1)*DATA_WIDTH-1            : j*DATA_WIDTH];
            wire signed [DATA_WIDTH-1:0] tap_hi = taps_bus[((DATA_DELAY-j)*DATA_WIDTH)-1 : (DATA_DELAY-1-j)*DATA_WIDTH];

            always @(posedge clk or posedge clr) begin
                if (clr)
                    presums_bus[(j+1)*STAGE1_WIDTH-1 : j*STAGE1_WIDTH] <= 0;
                else if (en)
                    presums_bus[(j+1)*STAGE1_WIDTH-1 : j*STAGE1_WIDTH] <= tap_lo + tap_hi;
            end
        end
    endgenerate

    always @(posedge clk or posedge clr) begin
        if (clr) valid_out <= 1'b0;
        else     valid_out <= en;
    end

endmodule
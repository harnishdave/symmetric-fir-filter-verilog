
module fir_pipeline #(
    parameter COEFF_NUM    = 6,
    parameter COEFF_WIDTH  = 8,
    parameter STAGE1_WIDTH = 13,
    parameter STAGE2_WIDTH = STAGE1_WIDTH + COEFF_WIDTH + 1,
    parameter STAGE3_WIDTH = STAGE2_WIDTH + $clog2(COEFF_NUM) + 1,
    parameter OUTPUT_WIDTH = STAGE3_WIDTH
)(
    input  wire                               clk,
    input  wire                               clr,
    input  wire                               valid_in,
    input  wire [COEFF_NUM*STAGE1_WIDTH-1:0]  presums_bus,
    input  wire [COEFF_NUM*COEFF_WIDTH-1:0]   coeff_bus,
    output reg  signed [OUTPUT_WIDTH-1:0]     data_out,
    output reg                                valid_out
);
    reg signed [STAGE2_WIDTH-1:0] mul_reg [0:COEFF_NUM-1];
    reg valid_s2;
    reg signed [STAGE3_WIDTH-1:0] accum;
    genvar j;
    integer k;

    generate
        for (j = 0; j < COEFF_NUM; j = j + 1) begin : gen_mul
            wire signed [STAGE1_WIDTH-1:0] sum_j  = presums_bus[(j+1)*STAGE1_WIDTH-1 : j*STAGE1_WIDTH];
            wire signed [COEFF_WIDTH-1:0]  coef_j = coeff_bus  [(j+1)*COEFF_WIDTH-1  : j*COEFF_WIDTH];

            always @(posedge clk or posedge clr) begin
                if (clr)           mul_reg[j] <= 0;
                else if (valid_in) mul_reg[j] <= sum_j * coef_j;
            end
        end
    endgenerate

    always @(posedge clk or posedge clr) begin
        if (clr) valid_s2 <= 1'b0;
        else     valid_s2 <= valid_in;
    end

    always @(posedge clk or posedge clr) begin
        if (clr) begin
            data_out  <= 0;
            valid_out <= 1'b0;
            accum     <= 0;
        end else begin
            valid_out <= valid_s2;
            if (valid_s2) begin
                accum = 0;
                for (k = 0; k < COEFF_NUM; k = k + 1)
                    accum = accum + mul_reg[k];
                data_out <= accum[OUTPUT_WIDTH-1:0];
            end
        end
    end

endmodule
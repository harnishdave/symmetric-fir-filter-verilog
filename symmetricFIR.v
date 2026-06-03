

module symmetricFIR #(
    parameter COEFF_NUM    = 6,
    parameter COEFF_WIDTH  = 8,
    parameter DATA_DELAY   = COEFF_NUM * 2,
    parameter DATA_WIDTH   = 12,

    parameter STAGE1_WIDTH = DATA_WIDTH + 1,
    parameter STAGE2_WIDTH = STAGE1_WIDTH + COEFF_WIDTH + 1,
    parameter STAGE3_WIDTH = STAGE2_WIDTH + $clog2(COEFF_NUM) + 1,
    parameter OUTPUT_WIDTH = STAGE3_WIDTH
)(
    input  wire                          clk,
    input  wire                          clr,
    input  wire                          load,
    input  wire signed [COEFF_WIDTH-1:0] coeff_value,
    input  wire signed [DATA_WIDTH-1:0]  noisy_signal,

    output wire signed [OUTPUT_WIDTH-1:0] filtered_signal,
    output wire                           output_valid
);

    wire [COEFF_NUM*COEFF_WIDTH-1:0]   coeff_bus;
    wire                               coeff_valid;
    wire [DATA_DELAY*DATA_WIDTH-1:0]   taps_bus;
    wire                               line_full;
    wire [COEFF_NUM*STAGE1_WIDTH-1:0]  presums_bus;
    wire                               preadd_valid;

    coeff_loader #(
        .COEFF_NUM   (COEFF_NUM),
        .COEFF_WIDTH (COEFF_WIDTH)
    ) u_coeff_loader (
        .clk         (clk), .clr (clr), .load (load),
        .coeff_value (coeff_value),
        .coeff_bus   (coeff_bus),
        .coeff_valid (coeff_valid)
    );

    delay_line #(
        .DATA_WIDTH (DATA_WIDTH),
        .DATA_DELAY (DATA_DELAY)
    ) u_delay_line (
        .clk      (clk), .clr (clr), .en (coeff_valid),
        .data_in  (noisy_signal),
        .taps_bus (taps_bus),
        .line_full(line_full)
    );

    pre_adder #(
        .COEFF_NUM    (COEFF_NUM),
        .DATA_WIDTH   (DATA_WIDTH),
        .DATA_DELAY   (DATA_DELAY),
        .STAGE1_WIDTH (STAGE1_WIDTH)
    ) u_pre_adder (
        .clk         (clk), .clr (clr), .en (line_full),
        .taps_bus    (taps_bus),
        .presums_bus (presums_bus),
        .valid_out   (preadd_valid)
    );

    fir_pipeline #(
        .COEFF_NUM    (COEFF_NUM),
        .COEFF_WIDTH  (COEFF_WIDTH),
        .STAGE1_WIDTH (STAGE1_WIDTH),
        .STAGE2_WIDTH (STAGE2_WIDTH),
        .STAGE3_WIDTH (STAGE3_WIDTH),
        .OUTPUT_WIDTH (OUTPUT_WIDTH)
    ) u_fir_pipeline (
        .clk         (clk), .clr (clr), .valid_in (preadd_valid),
        .presums_bus (presums_bus),
        .coeff_bus   (coeff_bus),
        .data_out    (filtered_signal),
        .valid_out   (output_valid)
    );

endmodule
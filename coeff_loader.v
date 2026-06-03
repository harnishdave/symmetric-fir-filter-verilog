
module coeff_loader #(
    parameter COEFF_NUM   = 6,
    parameter COEFF_WIDTH = 8
)(
    input  wire                             clk,
    input  wire                             clr,
    input  wire                             load,
    input  wire signed [COEFF_WIDTH-1:0]    coeff_value,
    output reg  [COEFF_NUM*COEFF_WIDTH-1:0] coeff_bus,
    output reg                              coeff_valid
);
    localparam INDEX_W = $clog2(COEFF_NUM);
    reg [INDEX_W-1:0] idx;
    integer k;

    always @(posedge clk or posedge clr) begin
        if (clr) begin
            idx         <= 0;
            coeff_valid <= 1'b0;
            for (k = 0; k < COEFF_NUM; k = k + 1)
                coeff_bus[k*COEFF_WIDTH +: COEFF_WIDTH] <= 0;
        end
        else if (load && !coeff_valid) begin
            coeff_bus[idx*COEFF_WIDTH +: COEFF_WIDTH] <= coeff_value;
            if (idx == COEFF_NUM - 1) begin
                coeff_valid <= 1'b1;
                idx         <= 0;
            end else begin
                idx <= idx + 1;
            end
        end
    end

endmodule
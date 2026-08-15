`timescale 1ns / 1ps
module testb_div_even;
    reg clk;
    reg rst_n;

    wire [15:0] clk_div;
    wire [15:0] error;
    integer fail_count;
    integer j;

    always #5 clk = ~clk;

    genvar i;
    generate
        for (i = 0; i < 16; i = i + 1) begin : div_case
            localparam integer DIV_VALUE = (i + 1) * 2;

            freq_divbyeven #(.NUM_DIV(DIV_VALUE)) uut (
                .clk(clk),
                .rst_n(rst_n),
                .clk_div(clk_div[i])
            );

            freq_divbyeven_checker #(.NUM_DIV(DIV_VALUE)) checker (
                .clk(clk),
                .rst_n(rst_n),
                .clk_div(clk_div[i]),
                .error(error[i])
            );
        end
    endgenerate

    initial begin
        clk = 0;
        rst_n = 0;
        #12 rst_n = 1;
        #1200;

        fail_count = 0;
        for (j = 0; j < 16; j = j + 1) begin
            if (error[j]) begin
                fail_count = fail_count + 1;
            end
        end

        if (fail_count == 0) begin
            $display("=========== Your Design Passed ===========");
        end
        else begin
            $display("=========== Test completed with %0d/16 NUM_DIV cases failing ===========", fail_count);
        end
        $finish;
    end
endmodule

module freq_divbyeven_checker #(
    parameter NUM_DIV = 6
)(
    input clk,
    input rst_n,
    input clk_div,
    output reg error
);
    reg [3:0] cnt;
    reg expected_clk_div;
    integer check_count;

    initial begin
        error = 0;
        check_count = 0;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cnt <= 4'd0;
            expected_clk_div <= 1'b0;
        end
        else if (cnt < NUM_DIV / 2 - 1) begin
            cnt <= cnt + 1'b1;
            expected_clk_div <= expected_clk_div;
        end
        else begin
            cnt <= 4'd0;
            expected_clk_div <= ~expected_clk_div;
        end
    end

    always @(negedge clk or negedge rst_n) begin
        if (!rst_n) begin
            error <= 0;
            check_count <= 0;
        end
        else begin
            check_count <= check_count + 1;
            if (clk_div !== expected_clk_div) begin
                error <= 1;
                $display("Failed NUM_DIV=%0d at check %0d: clk_div=%0d (expected %0d)",
                         NUM_DIV, check_count, clk_div, expected_clk_div);
            end
        end
    end
endmodule
`default_nettype none

module spi (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       sclk,
    input  wire       nCS,
    input  wire       copi,

    output reg        read_write,
    output reg [6:0]  address,
    output reg [7:0]  data
);

    /* ---------- Sampling ---------- */
    reg [1:0] sclk_samples;
    reg [1:0] ncs_samples;
    reg [1:0] copi_samples;

    always @(posedge clk) begin
        sclk_samples[0] <= sclk;
        ncs_samples[0]  <= nCS;
        copi_samples[0] <= copi;

        sclk_samples[1] <= sclk_samples[0];
        ncs_samples[1]  <= ncs_samples[0];
        copi_samples[1] <= copi_samples[0];
    end
    /* ---------- Sampling ---------- */

    /* ---------- SPI Transaction ---------- */
    wire sclk_rising_edge;
    wire ncs_falling_edge;
    wire ncs_rising_edge;
    
    assign sclk_rising_edge = ~sclk_samples[1] && sclk_samples[0];
    assign ncs_falling_edge = ncs_samples[1] && ~ncs_samples[0];
    assign ncs_rising_edge  = ~ncs_samples[1] && ncs_samples[0];

    reg [4:0] spi_cycle;
    reg transaction_ready;
    reg [15:0] spi_output;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            spi_cycle           <= 5'b0;
            transaction_ready   <= 1'b0;
        end else begin
            // Chip Select
            if (ncs_falling_edge) begin
                spi_cycle           <= 5'b0;
                transaction_ready   <= 1'b1;
            end
            
            // SPI Transaction
            if (sclk_rising_edge && transaction_ready) begin
                if (spi_cycle < 5'b10000) begin
                    spi_output  <= {spi_output[14:0], copi_samples[1]};
                    spi_cycle   <= spi_cycle + 1;
                end
            end

            // Parse COPI data
            if (ncs_rising_edge && transaction_ready && (spi_cycle == 5'b10000)) begin
                read_write  <= spi_output[15];
                address     <= spi_output[14:8];
                data        <= spi_output[7:0];
            end
        end 
    end
    /* ---------- SPI Transaction ---------- */

endmodule
/*
 * Copyright (c) 2024 Raiyan Samin
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_uwasic_onboarding_raiyan_samin (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);
  // All output pins must be assigned. If not used, assign to 0.
  assign uio_oe = 8'hFF;

  wire read_write;
  wire [6:0] address;
  wire [7:0] data;

  reg [7:0] en_reg_out_7_0;
  reg [7:0] en_reg_out_15_8;
  reg [7:0] en_reg_pwm_7_0;
  reg [7:0] en_reg_pwm_15_8;
  reg [7:0] pwm_duty_cycle;

  wire [15:0] pwm_out;

  // SPI
  spi spi_0 (
    .clk(clk),
    .rst_n(rst_n), 
    .sclk(ui_in[0]),
    .nCS(ui_in[2]),
    .copi(ui_in[1]),

    .read_write(read_write),
    .address(address),
    .data(data)
  );

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      en_reg_out_7_0  <= 0;
      en_reg_out_15_8 <= 0;
      en_reg_pwm_7_0  <= 0;
      en_reg_pwm_15_8 <= 0;
      pwm_duty_cycle  <= 0;
    end else begin
      if (read_write) begin
        case (address)
          7'h00: en_reg_out_7_0   <= data;
          7'h01: en_reg_out_15_8  <= data;
          7'h02: en_reg_pwm_7_0   <= data;
          7'h03: en_reg_pwm_15_8  <= data;
          7'h04: pwm_duty_cycle   <= data;

          default: begin 
            // do nothing for invalid addresses
          end
        endcase
      end
    end
  end

  // PWM 
  pwm_peripheral pwm_0 (
    .clk(clk),
    .rst_n(rst_n),
    .en_reg_out_7_0(en_reg_out_7_0),
    .en_reg_out_15_8(en_reg_out_15_8),
    .en_reg_pwm_7_0(en_reg_pwm_7_0),
    .en_reg_pwm_15_8(en_reg_pwm_15_8),
    .pwm_duty_cycle(pwm_duty_cycle),

    .out(pwm_out)
  );

  assign uo_out   = pwm_out[7:0];
  assign uio_out  = pwm_out[15:8]; 

  // List all unused inputs to prevent warnings
  wire _unused = &{ena, uio_in, ui_in[7:3], 1'b0};

endmodule

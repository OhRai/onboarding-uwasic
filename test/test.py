# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray

async def rising_edge(dut, signal):
    while int(signal.value) != 0:
        await ClockCycles(dut.clk, 1) 

    while int(signal.value) != 1:
        await ClockCycles(dut.clk, 1) 
    dut._log.info("Detected Rising Edge")

    return

async def falling_edge(dut, signal):
    while int(signal.value) != 1:
        await ClockCycles(dut.clk, 1) 

    while int(signal.value) != 0:
        await ClockCycles(dut.clk, 1) 
    dut._log.info("Detected Falling Edge")

    return

async def set_duty_cycle(dut, percent):
    duty_cycle_val = 255 if (percent == 1) else int(percent * 256)

    # Set Duty Cycle
    dut._log.info(f"Set duty cycle to {(percent*100):.2f}%")
    await send_spi_transaction(dut, 1, 0x00, 0xFF)
    await ClockCycles(dut.clk, 1000) 

    await send_spi_transaction(dut, 1, 0x01, 0xFF)
    await ClockCycles(dut.clk, 100)

    await send_spi_transaction(dut, 1, 0x02, 0xFF)
    await ClockCycles(dut.clk, 100)

    await send_spi_transaction(dut, 1, 0x04, duty_cycle_val)  # Set duty cycle
    await ClockCycles(dut.clk, 30000)

    # Calculations
    period = 0
    high_time = 0
    duty_cycle = 0

    if (percent == 0.00):
        await ClockCycles(dut.clk, 10000)
        assert (dut.uo_out[0].value == 0), "Expected duty cycle of 0%" 

    elif (percent == 1.00):
        start_time = cocotb.utils.get_sim_time(units="ns")
        await ClockCycles(dut.clk, 10000)
        end_time = cocotb.utils.get_sim_time(units="ns")
        assert (dut.uo_out[0].value == 1), "Expected duty cycle of 100%" 
        
        period = end_time - start_time
        high_time = period

        duty_cycle = (high_time / period)

        dut._log.info(f"Period: {period} ns")

    else:
        await rising_edge(dut, dut.uo_out[0])
        start_time = cocotb.utils.get_sim_time(units="ns") 

        await falling_edge(dut, dut.uo_out[0])
        high_end_time = cocotb.utils.get_sim_time(units="ns") 

        await rising_edge(dut, dut.uo_out[0])
        end_time = cocotb.utils.get_sim_time(units="ns")

        period = (end_time - start_time)
        high_time = (high_end_time - start_time)
        duty_cycle = (high_time / period)

    dut._log.info(f"Period: {period} ns")
    dut._log.info(f"High Time: {high_time} ns")
    dut._log.info(f"Duty Cycle: {(duty_cycle*100):.2f}%")

    return duty_cycle


async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

@cocotb.test()
async def test_pwm_freq(dut):
    # Write your test here
    dut._log.info("Start PWM Frequency test")

    # -------------------- Initialization -------------------- #
    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # Duty Cycle 50%
    dut._log.info("Set duty cycle to 50%")
    await send_spi_transaction(dut, 1, 0x00, 0xFF)
    await ClockCycles(dut.clk, 1000) 

    await send_spi_transaction(dut, 1, 0x01, 0xFF)
    await ClockCycles(dut.clk, 100)

    await send_spi_transaction(dut, 1, 0x02, 0xFF)
    await ClockCycles(dut.clk, 100)

    await send_spi_transaction(dut, 1, 0x04, 0x80)  # Set duty cycle to 50% (128 / 256)
    await ClockCycles(dut.clk, 30000)

    # -------------------- Testing Frequency -------------------- #
    # Since only the uo_out bits are being flipped between 0x00 and 0xFF, we can just check any bit of that
    # We can poll until we see changes

    await rising_edge(dut, dut.uo_out[0])
    start_time = cocotb.utils.get_sim_time(units="ns")

    await rising_edge(dut, dut.uo_out[0])
    end_time = cocotb.utils.get_sim_time(units="ns")

    # Period
    period = (end_time - start_time) * (10**(-9))
    frequency = 1 / period
    dut._log.info(f"Detected Frequency of {frequency:.2f} Hz")

    assert (frequency > (3000 - 3000*0.01) and frequency < (3000 + 3000*0.01)), "Expected frequency of 3 kHz, +- 1%"

    # maybe we can do this a few times with different values to ensure that frequency is 3khz? take average or smth idk
    
    dut._log.info("PWM Frequency test completed successfully")


@cocotb.test()
async def test_pwm_duty(dut):
    # Write your test here
    dut._log.info("Start PWM Duty Cycle test")

    # -------------------- Initialization -------------------- #
    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # -------------------- Duty Cycle Testing -------------------- #
    calculated_dc = await set_duty_cycle(dut, 0.00)
    assert (calculated_dc == 0), "Expected duty cycle of 0%" 

    calculated_dc = await set_duty_cycle(dut, 0.25)
    assert (calculated_dc > (0.25 - 0.25*0.01) and calculated_dc < (0.25 + 0.25*0.01)), "Expected duty cycle of 25%, +- 1%" 

    calculated_dc = await set_duty_cycle(dut, 0.5)
    assert (calculated_dc > (0.5 - 0.5*0.01) and calculated_dc < (0.5 + 0.5*0.01)), "Expected duty cycle of 50%, +- 1%" 

    calculated_dc = await set_duty_cycle(dut, 0.75)
    assert (calculated_dc > (0.75 - 0.75*0.01) and calculated_dc < (0.75 + 0.75*0.01)), "Expected duty cycle of 75%, +- 1%" 

    calculated_dc = await set_duty_cycle(dut, 1.00)
    assert (calculated_dc == 1), "Expected duty cycle of 100%" 

    dut._log.info("PWM Duty Cycle test completed successfully")

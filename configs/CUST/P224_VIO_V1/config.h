// SPDX-License-Identifier: GPL-3.0-or-later
// P224 VIO-v1: bench bring-up configuration, NOT flight validated.
#pragma once

#define FC_TARGET_MCU STM32H743
#define SYSTEM_HSE_MHZ 16
#define BOARD_NAME P224_VIO_V1
#define MANUFACTURER_ID CUST

#define USE_CONFIG_TARGET_PREINIT
#define USE_GYRO
#define USE_ACC
#define USE_GYRO_SPI_ICM42688P
#define USE_ACC_SPI_ICM42688P
#define GYRO_1_SPI_INSTANCE SPI2
#define GYRO_1_CS_PIN PD15
#define GYRO_1_EXTI_PIN NONE
// Provisional; verify six faces and rotation signs before any motor tests.
#define GYRO_1_ALIGN CW0_DEG
#define DEFAULT_GYRO_TO_USE GYRO_CONFIG_USE_GYRO_1
#define DEFAULT_PID_PROCESS_DENOM 4
#define SPI2_SCK_PIN PB13
#define SPI2_SDI_PIN PB14
#define SPI2_SDO_PIN PB15
#define SPI2_TX_DMA_OPT 14
#define SPI2_RX_DMA_OPT 15

// VBUS/PA9 is NOT connected. H743 VCP is supplied by the MCU target.
#define USB_DETECT_PIN NONE
#define UART2_TX_PIN PD5
#define UART2_RX_PIN PD6
#define UART4_TX_PIN PD1
#define UART4_RX_PIN PD0
#define UART7_TX_PIN PA15
#define UART7_RX_PIN PB3
#define UART8_TX_PIN PE1
#define UART8_RX_PIN PE0
// No receiver protocol or port is selected without actual receiver wiring.
#define DEFAULT_RX_FEATURE 0

// BF status LEDs are active-low by default; do not add LEDx_INVERTED.
#define LED0_PIN PC1
#define LED1_PIN PA0
#define LED2_PIN PC0

#define ADC_VBAT_PIN PA4
#define ADC_CURR_PIN PC4
#define ADC1_DMA_OPT 8
#define ADC3_DMA_OPT 9
#define DEFAULT_VOLTAGE_METER_SOURCE VOLTAGE_METER_ADC
#define DEFAULT_CURRENT_METER_SOURCE CURRENT_METER_ADC
#define DEFAULT_VOLTAGE_METER_SCALE 101
#define DEFAULT_CURRENT_METER_SCALE 500
#define DEFAULT_CURRENT_METER_OFFSET 0

#define MOTOR1_PIN PE9
#define MOTOR2_PIN PE13
#define MOTOR3_PIN PE11
#define MOTOR4_PIN PE14
#define TIMER_PIN_MAPPING \
    TIMER_PIN_MAP(0, PE9,  1, 0) \
    TIMER_PIN_MAP(1, PE13, 1, 1) \
    TIMER_PIN_MAP(2, PE11, 1, 2) \
    TIMER_PIN_MAP(3, PE14, 1, 3)
#define TIMUP1_DMA_OPT 10
#define DEFAULT_MOTOR_DSHOT_SPEED MOTOR_PROTOCOL_DSHOT300
// Start with the timer backend; validate one backend before trying bitbang.
#define DEFAULT_DSHOT_BITBANG DSHOT_BITBANG_OFF
// Enable bidirectional mode only after ESC firmware and wiring are confirmed.
#define DEFAULT_DSHOT_TELEMETRY DSHOT_TELEMETRY_OFF
// BMI088, MAG, BARO, SD, passive beeper, WS2812 and MOTOR5..8 are deferred.

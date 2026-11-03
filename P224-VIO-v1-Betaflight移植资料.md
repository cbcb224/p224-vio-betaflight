# P224 VIO-v1 — Betaflight 移植与云端编译资料

> 实施基线已确定为 Betaflight **2026.6.2**；工程入口见 [README](README.md)。下文 4.5.2 内容保留为历史源码审查示例，以本次锁定源码和工程配置为实施依据。

整理日期：2026-11-03。用途：把已完成 PX4 适配的同一块板移植到 Betaflight（BF）。本文件是硬件交接资料，不是已验证可用的 BF target。

## 移植目标（原文提供的偏好，实施前可调整）

- 厂商 p224，产品 vio-v1；建议自定义目标名 P224_VIO_V1，正式标识以所选 BF 版本的规则为准。
- Windows 编辑源码，仅 GitHub Actions 编译，不在本地编译。
- 每次构建生成唯一标识、源码提交、构建说明与可下载产物。
- 使用内部 Flash 保存配置；目标为多旋翼；前四路希望采用 BDShot300。

## MCU、时钟和调试


| 项目         | 硬件信息                                                                 |
| ------------ | ------------------------------------------------------------------------ |
| MCU          | STM32H743VIH6，TFBGA100，2 MB Flash                                      |
| 实机修订版   | STM32H743 rev. V                                                         |
| 外部晶振     | HSE 16 MHz，PH0/PH1                                                      |
| 调试烧录     | 可使用 ST-Link/SWD；PA13/PA14 保留                                       |
| 当前 PX4 CPU | 400 MHz；这是现有软件配置，不是 BF 必须沿用的值                          |
| USB          | PA11 DM、PA12 DP；PA9 未接，现有 PX4 配置输入上拉并关闭硬件 VBUS sensing |

BF 必须按实际封装和 16 MHz HSE 配置时钟。PA9 不可视作真实 USB 插拔检测。PA15/PB3/PB4 被外设占用，不能保留完整 JTAG，但可使用 SWD。

## 传感器与总线


| 总线 | 时钟     | MISO/SDA | MOSI | 器件与地址/片选                   |
| ---- | -------- | -------- | ---- | --------------------------------- |
| SPI1 | PA5      | PA6      | PA7  | BMI088 gyro CS=PA10；accel CS=PA2 |
| SPI2 | PB13     | PB14     | PB15 | ICM42688P CS=PD15                 |
| I2C1 | PB8 SCL  | PB9 SDA  | —   | 外部扩展                          |
| I2C4 | PD12 SCL | PD13 SDA | —   | IST8310=0x0E；实机 DPS310=0x76    |

**所有 IMU DRDY/INT 都未接。** PX4 已通过轮询工作，但不能据此推定 BF 同样支持。需逐项核对所选 BF 分支的陀螺采样、EXTI/轮询机制；不得编造一个未连接的中断脚。如果该 BF 版本必须依赖 DRDY，应明确提出硬件补线或驱动适配，而不是只做 target 配置。

首版仅使用 ICM42688P。官方当前支持列表明确列出 BMI088 不受支持，不能通过添加普通 target 宏启用，也不能用 BMI270 驱动替代；要使用 BMI088 需要独立驱动开发和验证。I2C4、IST8310、DPS310 的具体支持程度仍以所选 BF 源码为准。不能把 PX4 双 EKF/双 IMU 行为等同于 BF 的传感器选择机制。

### 实物轴向（从板顶视图定义；以机头为前）


| 传感器    | 芯片 X | 芯片 Y | 芯片 Z |
| --------- | ------ | ------ | ------ |
| BMI088    | 右     | 前     | 上     |
| ICM42688P | 前     | 左     | 上     |
| IST8310   | 前     | 右     | 上     |

PX4 当前 BMI088 使用 rotation=2，ICM/IST 使用 rotation=0；这些值依赖 PX4 驱动自带坐标变换，**不得直接复制为 BF alignment 枚举**。BF 要核对其驱动坐标变换后再映射，并实物逐轴验证。

## 九路输出——用户确认的逻辑顺序


| BF 逻辑输出候选编号 | 板上网络 | GPIO | 定时器/通道 |
| ------------------- | -------- | ---- | ----------- |
| 1                   | M1       | PE9  | TIM1_CH1    |
| 2                   | M2       | PE13 | TIM1_CH3    |
| 3                   | M3       | PE11 | TIM1_CH2    |
| 4                   | M4       | PE14 | TIM1_CH4    |
| 5                   | M5       | PB4  | TIM3_CH1    |
| 6                   | M8       | PB5  | TIM3_CH2    |
| 7                   | M7       | PB6  | TIM4_CH1    |
| 8                   | M6       | PB7  | TIM4_CH2    |
|                     | WS2812   | PB10 | TIM2_CH3    |

此表编号是物理资源顺序，不是 BF 四旋翼电机空间位置/旋转方向。仍需按实际机架分配电机，不能只凭 M1～M4 网络名推断左前/右后。

- 目标：前四路 BDShot300；其余四路保留可配置输出，BF 版本是否提供八路 motor/servo 资源需核对。
- PX4 使用 TIM1/DMA1 实现前四路双向 DShot；SPI1/2 RX/TX 使用 DMA2。BF DMA/DMAMUX 分配需重新计算，不复制 PX4 DMA 表。
- PX4 的“单定时器双向 DShot”限制来自其驱动，不代表 BF 相同限制。
- 实机只验证过 PX4 驱动初始化；未验证 ESC RPM 回传或实际输出波形。PWM_MAIN_TIM0=-4 和 DSHOT_BIDIR_EN=1 已写入 PX4 参数，尚未在重启后复查；这些不是 BF 参数。

## 串口


| MCU 外设 | TX   | RX  | 现有 PX4 名称 |
| -------- | ---- | --- | ------------- |
| USART2   | PD5  | PD6 | ttyS0/TEL1    |
| UART4    | PD1  | PD0 | ttyS1/TEL2    |
| UART7    | PA15 | PB3 | ttyS2/TEL3    |
| UART8    | PE1  | PE0 | ttyS3/TEL4    |

BF 按 MCU 串口编号映射，不沿用 ttyS/TEL 编号。未指定 SBUS/CRSF/ELRS 接收机，没有确认反相/半双工硬件；不要擅自设置。GPS、外设回环、四串口实际收发尚未全部验证。

## 电压、电流与其他 IO


| 功能         | GPIO/参数                             |
| ------------ | ------------------------------------- |
| 电池电压     | PA4，ADC1_IN18；上臂200kΩ、下臂22kΩ |
| 电池电流     | PC4，ADC1_IN4；分流1mΩ、放大50倍     |
| ADC参考      | 3.3 V                                 |
| 蜂鸣器       | PC7，TIM8_CH2，高有效驱动无源蜂鸣器   |
| 红/绿/蓝 LED | PC1 / PA0 / PC0；共阳，低有效         |

物理换算：电池电压=ADC输入电压×10.09090909；电流=ADC输入电压×20 A/V（未含零点）。BF 的电压/电流 scale 单位、分辨率和内部公式需按版本换算，不能直接填 PX4 BAT1 参数。当前仅 USB 供电时两路 ADC 为0，未完成真实电池/电流校准。

无源蜂鸣器需要波形驱动，不能只映射普通高低电平的有源蜂鸣器功能。BF 是否可使用 TIM8_CH2 实现该方式需核对。

## SD 与不具备的硬件

SDMMC1：PC12 CK、PD2 CMD、PC8/9/10/11 D0/1/2/3；无卡检测。原文称 PX4 能挂载，当前目录无实测记录可供复核。

未提供外置 OSD、外置 Flash、FRAM、安全按钮、反相器、电源控制、CAN 收发器等连接。不得借用其他 H743 target 中相似但未实际连接的资源。

## 现有 PX4 和 BF 烧录布局的边界

现有 PX4：bootloader 0x08000000～0x0801FFFF；应用0x08020000～0x081DFFFF；参数0x081E0000～0x081FFFFF。私有 PX4 board ID=60000。

这些地址、板卡 ID、参数格式都属于 PX4，**BF 不得默认使用 PX4 的0x08020000应用偏移**。应按实际 BF target、链接脚本和烧录镜像核对地址。切换前保留 PX4 恢复产物和参数；不要假定当前 PX4 bootloader 能加载 BF。


## 已验证和未验证

原文报告已验证（PX4固件；本次未取得日志、源码或实板独立复核）：USB/MAVLink；两组 IMU、IST8310、DPS310 通信与健康；姿态/EKF对齐；内部 ADC3 温度通道；CPU约38.5%、RAM约27.9%；前四路DShot及其余四路PWM驱动初始化。

未验证：BF运行、无DRDY时BF采样时序、BF传感器轴向、BDShot300波形/RPM、各电机资源顺序、实际电池/电流比例、四串口外设、蜂鸣器波形、SD写入。

## BF 首版验收顺序

1. 固定 BF release/tag，核对支持硬件，建立独立目标配置与 Actions；保留完整构建标识。
2. 确认 MCU/HSE/Flash 链接布局，先云端构建，不自动烧录。
3. 上板验证 USB/MSP、ICM采样和无DRDY机制；逐轴动作检查 alignment。
4. 核对九路资源/定时器/DMA；拆桨、人工确认接线和电调供电后，再做输出与RPM测试。
5. 校准真实电压/电流、检查串口及蜂鸣器；最后再考虑BMI088/磁力计/气压计与SD。

## 原始证据与参考

- 原始硬件表：.codex/引脚定义-P224-AIO-V1.0.md（其中TIM5冲突已确认采用HRT=TIM5、OS tick=SysTick；此为PX4决策，不要求BF沿用）。
- 实机与操作记录：P224-AIO-工作记录.md。
- 现有配置：boards/p224/vio-v1；最后验证的PX4应用源码af0c6eb375d332ce1efe7328b67417e26ec926ee，Actions #10。
- BF官方自定义板文档：https://betaflight.com/docs/development/Custom-Board-Configuration
- BF官方配置文件指南：https://betaflight.com/docs/development/manufacturer/creating-configuration
- BF官方目标配置库：https://github.com/betaflight/config

官方指南以 config.h 描述自定义目标；具体配置形式、编译方式和支持宏必须与选择的BF版本一致。


## 2026-11-03 审查结论与证据边界

本次只取得本 Markdown，目录内没有原理图、PCB、PX4 工程、实机日志或 Betaflight 工程。以下区分“原文硬件声明”“官方源码已核对”“待实机验证”。不能据此宣布引脚表已通过原理图审查或固件已可飞行。原文的 Windows/GitHub Actions 等是文档中的实施偏好，本次请求仅授权审查和完善资料，并未实际创建远程仓库、启动构建或烧录。

主要问题不是引脚表中已经证明存在大量错误，而是缺少可复现的版本基线、对不支持器件的明确处置，以及构建和台架验收条件。结论：可以继续准备 ICM42688P 单 IMU 的 BF 首版，但当前资料还不是可直接烧录的 target。

| 项目 | 本次结论 | 实施处理 |
| --- | --- | --- |
| BMI088 | 官方当前传感器列表明确不支持 | 首版排除；后续若需要，另立驱动开发任务 |
| ICM42688P 无 DRDY | BF 4.5.2 存在无中断读取分支，并非必然无法工作 | EXTI 不绑定虚假 GPIO；按选定版本配置 NONE 或不定义，验证周期与数据更新 |
| 无源蜂鸣器 | BF 4.5.2 已有定时器 PWM 蜂鸣器路径 | PC7 除 BEEPER 资源外还要有可分配的 TIM8_CH2 和非零频率 |
| ADC 比例 | 可以从 BF 4.5.2 公式得到候选参数 | 电压 scale≈101，电流 scale=500；见后文完整条件 |
| 配置目录 | 不同年代源码解析规则不同 | 旧版平铺目录与新版厂商分组目录不能混用 |
| 九路输出 | 实际为八路候选电机输出加一路 LED 灯带 | WS2812 不计入电机数，四旋翼只启用四台电机 |
| 其他硬件 | 未提供独立证据 | 保留待验证标记，不复制其他板卡的默认外设 |

### 版本基线与配置目录必须配套

本次用 **Betaflight 4.5.2 标签**核对了若干关键源码，用作可复查的历史例子，不表示它是当前最新版本或已确定的最终版本。正式实施先选择受维护的稳定 release，再固定固件完整 commit SHA 和配置仓库完整 commit SHA；更新版本要重新核对下面的代码路径和参数。

- BF 4.5.2 的 `mk/config.mk` 查找 `configs/<BOARD_NAME>/config.h`。候选路径为 `src/config/configs/P224_VIO_V1/config.h`，构建入口为 `make CONFIG=P224_VIO_V1`；不要同时传 `TARGET` 和 `CONFIG`。
- 当前官方指南使用 `configs/<MANUFACTURER_ID>/<BOARD_NAME>/config.h`，自制板可使用保留厂商 ID `CUST`。`p224` 是用户提供的厂商名称，不等于已注册的 BF manufacturer ID；产品名、板名、四字符板标识和厂商 ID 是不同字段，应按对应版本分别填写。
- 4.5.2 的 `make configs` 会克隆或拉取配置仓库。因此“旧固件标签 + 每次拉最新 config master”不能作为可靠构建流程；应单独检出兼容配置提交，并放入该版本实际接受的目录。固定版本后不要再执行会更新配置的命令。
- 板名 `P224_VIO_V1` 暂作私有候选；以构建脚本能解析、命名规则允许且不重名为最终条件。对外提交目标另按官方要求处理。

### 单 IMU 首版的配置审查清单

这是配置输入表，不是已通过编译的 `config.h`，不要把表内候选项直接拼接后当作可用固件。

| 功能 | 首版要求 |
| --- | --- |
| MCU / HSE | STM32H743 / 16 MHz；4.5.2 构建脚本读取 `FC_TARGET_MCU` 和 `SYSTEM_HSE_MHZ` |
| USB | 启用 USB VCP/MSP；复核 H743 USB 初始化与未接 VBUS 的行为，不机械复制 PX4 的 PA9 上拉 |
| IMU | SPI2 PB13/PB14/PB15，CS PD15；4.5.2 驱动由 `USE_GYRO_SPI_ICM42688P` 控制，相应加速度计使能项也须核对 |
| 未使用 IMU | BMI088 的 PA10、PA2 CS 应维持不选中状态；如开启 SPI1，更要核对上电和初始化期间 CS 不浮空 |
| 陀螺 EXTI | 未连接，使用版本支持的 NONE/缺省表示；不占用其他 GPIO 假装接线 |
| 串口 | UART2/4/7/8 加 USB VCP；核对该版本端口计数规则、RX/TX 资源与 USB MSP 默认开通 |
| 输出 | MOTOR1..4 对应 PE9/PE13/PE11/PE14；计时器通道顺序为 CH1/CH3/CH2/CH4 |
| LED | 三颗共阳 LED 按低有效处理；WS2812 PB10 是独立灯带功能，首版可暂不启用 |
| 其他功能 | 首轮可不启用 MAG、BARO、SD、LED_STRIP、其余输出，减少同时验证的变量 |

### 无 DRDY 的源码证据和验收要求

BF 4.5.2 的 `icm426xxSpiGyroDetect()` 将读取函数设置为 `mpuGyroReadSPI()`。后者在初始化阶段未检测到足够 EXTI 时，进入 `GYRO_EXTI_NO_INT`，通过 SPI 发起读取并等待完成。该分支证明存在无中断读取方案，但不证明此板已达到稳定的控制时序；也不能由此宣称已使用中断触发 DMA。

先以保守 PID 循环频率（例如 2 kHz，须确认该版本接受此设置）测试，记录陀螺报告频率、PID 频率、任务负载、异常计数和静置/转动数据。提高频率前检查重复样本、更新间隔和负载；必要时记录调试数据。不能把“成功识别 WHO_AM_I”“姿态模型会动”当作高频采样验收。若最终版本没有稳定回退路径，再评估从 ICM INT 引脚补线到可用 EXTI GPIO 或进行驱动适配。

### BDShot300 的资源与时序补充

- BF 中通常选择 DSHOT300，再启用双向 DShot；双向 RPM 回传与 UART ESC telemetry 是两条不同数据通路，不要求为 RPM 回传另占串口。
- 必须确认电调型号、固件版本和双向 DShot 支持情况，并填写实际电机磁极数；当前均未提供。
- 前四路同属 TIM1，应一起确定输出协议和更新频率。后四路 PWM/servo 是候选用途，并不代表 BF 默认四旋翼混控会驱动它们；同一定时器上的通道还受共享时基约束。
- DShot300 帧长约 53.3 μs，双向模式还需要换向、回传和间隔。ICM 的 8 kHz 采样不意味着 PID 必须运行 8 kHz；首版采用保守 PID 频率，再依据该版本协议限制与实测调整。
- 核对定时器映射、GPIO AF、DMA/DMAMUX、DShot bitbang/定时器后端及冲突；不能只检查引脚具备 TIM 通道。保存最终 `resource`、`timer`、`dma` 输出（以版本支持的命令为准）。
- 拆桨验证四路单独起转、实际位置和方向；记录每路 RPM、回传错误和波形。只显示 DSHOT300 或初始化成功不算双向验收。

### ADC 参数换算（明确限定 BF 4.5.2）

以下是理想元件值的起点，需先确认实际电路、采样稳定性及该版本 H7 ADC 引脚映射。

1. 分压比 `(200+22)/22 = 10.090909`。由 `voltage.c` 公式，当 `vbatresdivval=10`、`vbatresdivmultiplier=1` 时，实际倍率为 `vbat_scale/10`，故 `vbat_scale=101` 是接近值，理想比例误差约 +0.09%。不能填成 10 或 1009。
2. 电流灵敏度 `0.001 Ω × 50 = 0.05 V/A = 50 mV/A`。`current.c` 的 scale 单位为 mV/10A，所以 `ibata_scale=500`；不能将 20 A/V 直接填入该字段。
3. 在该版本，`ibata_offset` 是换算后相加的 mA 修正值，候选初值为 0。若零电流读数为正，需向负方向修正；先用 `get` 检查版本允许范围，不能把 ADC 电压偏移原样作为该值输入。
4. 候选 CLI：先确认存在 `vbat_scale`、`vbatresdivval`、`vbatresdivmultiplier`、`ibata_scale`、`ibata_offset`，再设置上述值并选择 ADC 电压/电流来源。这里不提供自动执行脚本，避免跨版本套用。
5. 用万用表测多个电压点；电流用已知负载和参考表测零点及多个负载点，并检查 mAh 积分。比例校准可按 `新 vbat_scale = 旧值 × 实测电压 / BF显示电压`、`新 ibata_scale = 旧值 × BF显示电流 / 实测电流` 迭代，电流比例调整前先扣除零点误差。

按名义 3.3 V 算，电压测量满量程约 33.3 V，电流单向满量程约 66 A（还受放大器输出摆幅限制）。这些只是 ADC 理论范围，不能推断整板可用电池串数或持续载流能力。200k/22k 的等效源阻抗约 19.8kΩ，需核对 ADC 采样时间、滤波和输入建立时间；标称 3.3 V 也不等于实测参考电压。

### 蜂鸣器、I2C、SD 与配置存储

- `sound_beeper.c` 在 `USE_BEEPER` 和 `USE_PWM_OUTPUT` 条件下支持定时器蜂鸣器。需给 PC7 提供可分配的 TIM8_CH2，并设置非零 `beeper_frequency`；频率按器件规格选取。检查禁鸣时输出、上电默认电平和驱动电路，PWM 路径的极性处理不能靠普通蜂鸣器的 inverted 设置想当然推断。
- I2C4 的 PD12/PD13 需在所选版本 H743 引脚表中查到，并确认驱动能使用该总线；仅在芯片 AF 表合法还不够。核对板上上拉、电压、七位地址和两器件同时探测。DPS310 和 IST8310 在当前官方支持列表中，但列表反映 master，不保证历史版本行为相同；IST8310 另有特殊轴向问题。
- SDMMC 黑匣子需核对 BF 的 H7 SD 驱动、4-bit/1-bit 模式、无卡检测配置、DMA/缓存一致性和文件系统；按冷启动有卡/无卡、持续写入、记录文件可解码逐项验收。未启用 SD 时可考虑 MSP/串口日志，不能把内部参数 Flash 自动当黑匣子。
- BF 内部 Flash 参数保留区域由其链接与存储代码确定。核对应用区与配置区不重叠，并测试 `save` 后完全断电重启仍保留。PX4 的最后一个 128 KB 参数扇区不能直接沿用。

### GitHub Actions 构建交付契约

当前没有目标配置和远程仓库，因此本节是后续实施规范，不是已经跑通的 workflow。

1. 使用 Linux runner；在工作流中固定固件 SHA、兼容配置 SHA、工具链版本及板配置版本。固件仓库按要求取得子模块，使用所选 release 对应的依赖安装步骤。
2. 先校验配置路径、MCU、16 MHz HSE 和预期板名，防止落入默认 target；再调用该版本支持的工具链安装和构建命令。4.5.2 的入口示例为 `make CONFIG=P224_VIO_V1`，不能认为此单条命令已包含整个 CI 环境准备。
3. 每次产物名包含板名、固件 SHA、配置版本、Actions run ID 和 attempt。把本次修改后的配置单独保存并计算 SHA256，不能只写上游 config 仓库 SHA 而遗漏私有修改。
4. 保存 HEX、ELF、MAP、完整构建日志、实际配置和清单；若交付 BIN，必须同时交付经链接结果确认的烧录起始地址。HEX 含地址信息，仍须检查其记录范围与最终 ELF。
5. 清单记录仓库地址、完整 SHA、工作区修改、编译选项、工具链、链接脚本、Flash/参数区、构建 URL、时间和每个文件的 SHA256。上传产物缺失时应让作业失败，并写明保留期限。
6. 编译通过仅证明静态构建成功；必须保留“未上板验证”标识，直到完成对应实测。不要在构建作业中加入自动擦除或烧录动作。

### 烧录前恢复条件与台架通过标准

切换前取得 PX4 bootloader、应用固件、完整参数备份和恢复步骤；核对文中 PX4 路径/commit/Actions #10 对应的实际仓库与可下载产物。当前目录未包含它们。确认 SWD 可连、NRST/BOOT0 实际可访问性、供电与恢复方式。BOOT0/ROM DFU 接法尚未提供，不应承诺能用按键进入 DFU。

首刷前由 HEX/ELF/MAP 确认 BF 地址；若覆盖 0x08000000，意味着可能覆盖 PX4 bootloader，需要预先具备 SWD 恢复能力。是否全片擦除按实际存储布局决定，并记录其影响。

| 阶段 | 通过条件 | 失败时处理 |
| --- | --- | --- |
| USB与启动 | 冷启动可连 MSP，板名/版本/HSE一致，无持续复位 | 停留在启动与时钟排查，不接电调做输出试验 |
| IMU | 识别 ICM，六面静置和逐轴旋转方向正确，频率/负载稳定 | 检查轴向、读取时序、电源和 SPI |
| 配置存储 | 修改一项配置、保存、彻底断电后读回一致 | 检查 Flash 布局和存储机制 |
| 输出 | 拆桨逐路位置/方向正确，四路双向 RPM 稳定 | 检查资源、DMA、电调固件和信号波形 |
| 供电与IO | 电池/USB分别上电正常，ADC校准，所需串口与蜂鸣器通过 | 记录未通过功能，不能标注整板验收完成 |
| 飞行准备 | 接收机通道、解锁、失控保护、模式与电机停止行为通过 | 尚未指定接收机，此阶段当前无法关闭 |

每项记录固件 SHA、配置哈希、测试条件、预期/实测、日志位置和结论。首次飞行前另完成机架配置、PID/滤波与失控保护检查；PX4 EKF 正常不是 BF 通过依据。

## 本次核对的官方依据

以下固定标签源码是本次具体推导的依据；带 current 的网页随上游变化，不能代替固定版本核验。

- [官方传感器支持列表（反映 master）](https://betaflight.com/docs/wiki/guides/current/Supported-Sensors)：BMI088 不支持；ICM42688P、DPS310、IST8310 支持范围及注意事项。
- [当前官方配置指南](https://betaflight.com/docs/development/manufacturer/creating-configuration)：新目录结构、厂商标识及构建选择方式。
- [BF 4.5.2 mk/config.mk](https://github.com/betaflight/betaflight/blob/4.5.2/mk/config.mk)：旧目录解析、HSE 读取、配置仓库更新行为。
- [BF 4.5.2 Makefile](https://github.com/betaflight/betaflight/blob/4.5.2/Makefile)：CONFIG/TARGET、产物及链接调用。
- [BF 4.5.2 ICM 驱动](https://github.com/betaflight/betaflight/blob/4.5.2/src/main/drivers/accgyro/accgyro_spi_icm426xx.c) 与 [MPU公共SPI读取](https://github.com/betaflight/betaflight/blob/4.5.2/src/main/drivers/accgyro/accgyro_mpu.c)：ICM读取函数与无中断分支。
- [BF 4.5.2 voltage.c](https://github.com/betaflight/betaflight/blob/4.5.2/src/main/sensors/voltage.c) 与 [current.c](https://github.com/betaflight/betaflight/blob/4.5.2/src/main/sensors/current.c)：ADC 换算公式。
- [BF 4.5.2 sound_beeper.c](https://github.com/betaflight/betaflight/blob/4.5.2/src/main/drivers/sound_beeper.c)：无源蜂鸣器 PWM 路径。


## 2026.6.2 实施进展

已下载官方源码 e0b7bb01b17b21351057e9ead2d1ab39dd44fa16，上游 config gitlink 为 3a406c5c30c20d7c3bc7dd5ed547cca961baf0a9。已建立独立配置、版本锁定、Actions 工作流和产物检查脚本，尚未云端编译或上板。

本次本地源码确认：无 DRDY 读取分支仍存在；H743 ADC 表包含 PA4/PC4；USB FS 关闭硬件 VBUS sensing；LED 默认低有效，不应额外定义 LEDx_INVERTED。ADC 公式保持一致。原生 H743 Flash 配置区实际位于 0x08020000..0x0803FFFF，不是 PX4 参数区；向量起始 0x08000000，主代码区从 0x08040000 开始。

首版只映射四路电机、默认 DShot300 且双向 OFF，待电调信息与台架确认后启用；CW0_DEG 轴向只是临时测试值。蜂鸣器、SD、I2C外设和额外输出留待后续。完整配置范围及上传方法见 README。


## 首次云端构建已通过

2026-11-03 已通过 GitHub 插件提交工程并完成 [Actions #1](https://github.com/cbcb224/p224-vio-betaflight/actions/runs/41585512669)，工程提交 9247ca9002ac955c87541de4379f095bffc66822。HEX/BIN 编译、真实链接布局检查和产物上传均成功；15 个产物文件可在该作业下载。前述“尚未云端编译”记录描述的是准备阶段，以本节为最新状态。实板验证仍未进行。

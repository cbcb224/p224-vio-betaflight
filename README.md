# P224 VIO-v1 Betaflight 首版工程

当前状态：首次 GitHub Actions 云端编译成功，HEX/BIN、链接检查和产物上传已通过；未上板验证，不能作为已验收飞行固件。

仓库：https://github.com/cbcb224/p224-vio-betaflight

首次成功构建：[Actions #1](https://github.com/cbcb224/p224-vio-betaflight/actions/runs/41585512669)，工程提交 `9247ca9002ac955c87541de4379f095bffc66822`。

## 固定基线

- 固件：Betaflight **2026.6.2**，完整 SHA 见 `source-lock.json`。
- 目标：`P224_VIO_V1`，自制厂商标识 `CUST`。
- MCU：STM32H743VIH6，2 MB Flash，HSE 16 MHz。
- 单 IMU：SPI2 ICM42688P，CS PD15，EXTI NONE。BMI088 不启用，通过 preinit 保持两个 CS 高电平。
- 本地修改，Linux GitHub Actions 编译；没有本地编译步骤。

## 目录与修改入口

| 路径 | 用途 |
| --- | --- |
| `configs/CUST/P224_VIO_V1/config.h` | 引脚、默认参数、DMA、传感器定义；首要修改入口 |
| `configs/CUST/P224_VIO_V1/config.c` | 未使用 BMI088 的 CS 预初始化 |
| `source-lock.json` | 固件 SHA、上游配置 SHA、工具链版本 |
| `.github/workflows/build-p224.yml` | 手动或提交触发云端构建 |
| `scripts/prepare.py` | 校验源码版本、应用补丁、记录输入哈希 |
| `scripts/package.py` | 收集产物，校验 HEX 范围、启动向量及配置区符号 |
| `patches/` | 可选 BF 源码补丁；当前无驱动补丁 |
| `firmware/` | 本地下载的官方源码，已忽略，不上传到工程仓库 |

云端通过 BETAFLIGHT_CONFIG 指向本工程根目录，使用自己的 configs/；不会把配置塞进其他厂商的目标。上游配置 SHA 记录的是固件 gitlink，不是本板私有配置版本；本板以工程提交 SHA 和配置文件 SHA256 标识。

## 首版已配置范围

- USB VCP/MSP；USB_DETECT_PIN=NONE，PA9 不占用。所选 H7 USB FS 初始化已关闭硬件 VBUS sensing。
- UART2 PD5/PD6、UART4 PD1/PD0、UART7 PA15/PB3、UART8 PE1/PE0。尚未指定接收机协议和端口。
- 三色状态灯 PC1/PA0/PC0：BF LED 驱动默认低有效，**不定义 LEDx_INVERTED**。
- ADC 电压 PA4、ADC 电流 PC4；源码 H7 ADC 表支持这两脚；候选 scale 为 101/500，仍须校准。
- MOTOR1..4：PE9/PE13/PE11/PE14；TIM1 CH1/CH3/CH2/CH4；DSHOT300。
- 陀螺 CW0_DEG 为**临时测试值，轴向未验证**；不能从 PX4 rotation 直接推得。默认 PID denominator=4（ICM 8 kHz 时约 2 kHz），以实机 status/tasks 为准。
- 默认采用定时器 DShot 后端，双向回传 OFF。确认电调固件、线序、轴向和电机磁极数后，再在台架启用 `dshot_bidir` 并测试；因此首版默认尚不是已启用的 BDShot300。

暂不映射 MOTOR5..8、无源蜂鸣器 PC7、WS2812 PB10、SD、I2C1/4、DPS310 和 IST8310；物理引脚记录仍在移植资料中。MCU target 可能编译通用功能代码，未映射不代表完全从二进制裁掉相关驱动。先关闭第一轮台架验收，再逐项启用。

### 首版 DMA 候选分配

按锁定源码的 H7 DMAMUX 表：opt 0..7 对应 DMA1 stream0..7，opt 8..15 对应 DMA2 stream0..7。

| 用途 | DMA opt | 候选通道 |
| --- | --- | --- |
| MOTOR1/2/3/4 | 0/1/2/3 | DMA1 stream0/1/2/3 |
| ADC1 / ADC3 | 8 / 9 | DMA2 stream0 / 1 |
| TIM1 update | 10 | DMA2 stream2 |
| SPI2 TX / RX | 14 / 15 | DMA2 stream6 / 7 |

SPI2 无 DRDY 模式不是中断触发 DMA；配置 DMA 资源不等于实际使用该模式。以上尚需 `resource`、`timer`、`dma` 与波形/RPM 实测，后续启用额外资源必须重新检查冲突。

## 上传与首次云端编译

1. 在自己的 GitHub 账号新建空仓库，例如 `p224-vio-betaflight`。GitHub Actions 需要可用额度及仓库 Actions 权限。
2. 将本工程上传到仓库根目录，**包含隐藏目录 `.github`、configs、scripts、source-lock.json、README、patches 和移植资料**。不要上传 firmware/、dist/ 或 __pycache__/。
3. 推送后进入 Actions → Build P224 VIO-v1；首次会由文件提交触发，也可使用 Run workflow 手动运行。初次下载工具链和依赖需要时间。
4. 绿色完成后下载该次 Artifact；其中应包含 HEX、BIN、ELF、MAP、构建日志、工具链版本、板配置、链接脚本、manifest 和 SHA256SUMS。失败作业只上传诊断包，不可当作固件使用。
5. 后续只改板配置即可提交触发新构建。若需改驱动，编辑本地 firmware/ 源码并按 patches/README.md 导出补丁；源码修改不自动上传，必须把补丁提交。

远程仓库已创建为公开仓库，首次构建已完成。后续本地修改 configs/ 或 scripts/ 后，通过 GitHub 插件提交会自动触发新构建。首次产物保留至 2027-01-02；需要长期留存请下载备份。

## 首刷地址与恢复

锁定 H743 链接脚本为 `stm32_flash_h743_2m.ld`：

- 启动/向量：0x08000000..0x0801FFFF。
- BF 内部配置：0x08020000..0x0803FFFF。
- 主代码区：0x08040000..0x081FFFFF。

这是 BF 原生 Flash 布局，**将覆盖现有 PX4 bootloader 的地址范围**。先保存 PX4 恢复固件和参数，并确认 ST-Link/SWD 可恢复。HEX 按内含地址烧录；BIN 基址是 0x08000000，不能写到 PX4 的 0x08020000。package.py 会核对链接结果，但仍不能代替烧录前复核。没有自动烧录步骤。

## 台架验收记录

全程先拆桨。首轮仅接 USB，读取 `version`、`status`、`tasks`、`resource`、`timer`、`dma`、`diff all`（以该版本实际支持为准），保存原始输出和构建 manifest。

1. USB可枚举；板名、版本、陀螺和加速度计识别正常，无持续重启。
2. 六面静置、逐轴动作验证加速度计/陀螺符号和模型运动；完成轴向配置后再做输出测试。
3. 核对无 DRDY 的实际采样更新、任务负载、是否出现持续重复数据或停顿。
4. 保存一项参数，彻底断电重启后读回；确认 Flash 配置保留。
5. 电调接线和供电人工复核后，拆桨逐路确认位置、方向，再启用双向 DShot，记录每路 RPM 与错误率；磁极数按实际电机填写。
6. 分别进行电池/USB上电与 ADC 校准、所需串口回环测试。接收机、失控保护和解锁条件尚未确定，当前不能标注飞行验收完成。

资料依据是用户的引脚表和锁定版本官方源码，尚无原理图/实板独立复核。遇到启动、轴向或时序异常时停止推进输出测试并保留日志。

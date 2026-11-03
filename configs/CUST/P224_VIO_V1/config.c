// SPDX-License-Identifier: GPL-3.0-or-later
#include "drivers/io.h"

void configTargetPreInit(void)
{
    // Keep the unsupported BMI088 gyro/accelerometer deselected.
    ioPreinitByIO(IOGetByTag(IO_TAG(PA10)), IOCFG_OUT_PP, PREINIT_PIN_STATE_HIGH);
    ioPreinitByIO(IOGetByTag(IO_TAG(PA2)), IOCFG_OUT_PP, PREINIT_PIN_STATE_HIGH);
}

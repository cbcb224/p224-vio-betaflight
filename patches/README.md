# 源码修改

当前不需要驱动补丁。板级定义在 configs/，不要改官方同名板。

如需修改本地 firmware/ 内已跟踪源码，在 PowerShell 导出补丁：

```powershell
git -C firmware diff --binary --output=../patches/0001-driver-change.patch
```

将补丁和板配置一起上传。CI 在锁定源码上按文件名顺序应用 *.patch。
新增源码文件必须纳入 diff 后才能导出。不要手工删除其他人的源码改动。
本地 prepare.py 仅在源码未改动时运行；已有修改时会明确停止，避免覆盖。

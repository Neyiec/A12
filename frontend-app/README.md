# Android 联调

Web 源码在 `../frontend`；Android Studio 运行的是同步到 `android/app/src/main/assets/public` 的静态构建，不使用 Vite 代理。

## Android Studio 模拟器

在本目录执行 `npm run sync:android:emulator`，然后在 Android Studio 重新运行 App。也可执行 `npm run run:android:emulator` 完成同步并选择模拟器运行。

专用构建模式读取 `../frontend/.env.android-emulator`：

- Java API：`http://10.0.2.2:8088`
- Python API：`http://10.0.2.2:8001`
- mock 关闭，使用真实后端账号。

`10.0.2.2` 是 Android Studio 模拟器访问电脑的地址。

## Android 真机（USB）

启动本机 Java（8088）和 Python（8001）。在手机上启用 USB 调试并授权电脑，确认 `adb devices` 中真机的状态为 `device`。在本目录的 PowerShell 窗口执行：

```powershell
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8088'
$env:VITE_PYTHON_API_BASE_URL = 'http://127.0.0.1:8001'
npm run sync:android:emulator
adb -d reverse tcp:8088 tcp:8088
adb -d reverse tcp:8001 tcp:8001
```

然后在 Android Studio 选择真机并运行 App。USB 重新连接后，需重新执行两条 `adb reverse` 命令。如果电脑有多个 USB 真机，用 `adb -s <序列号>` 代替 `adb -d`。

Java 和 Python 都须允许 WebView 来源 `http://localhost`。如果 Python 尚未允许，请在现有 `A12_FRONTEND_ORIGINS` 配置中添加该来源后重启 Python。使用真机局域网联调时，可将两个 API 地址改为电脑的局域网地址。

修改 Web 源码或 API 地址后都要重新构建、同步、安装 App。模拟器专用模式不修改 Web 的 production 配置。

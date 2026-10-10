# 本地 / OSS 存储切换

当前 `application.yaml` 默认使用 OSS。测试本地存储时设置 `A12_STORAGE_PROVIDER=local` 并重启 Java。前端上传接口不变，本地模式下个人资源与后台公共资源写到 Java 启动目录下的 `data/uploads`。

建议在 IDEA 环境变量中固定绝对目录：

```text
A12_STORAGE_LOCAL_DIR=D:/GitRepositories/A12/backend-java/A12/data/uploads
A12_STORAGE_LOCAL_BASE_URL=http://localhost:8088
```

本地文件通过有效期签名读写，不是公开静态目录；重启 Java 后旧签名失效，需要重新获取上传或下载地址。单文件限制 100 MiB。Python 与 Java 同机运行时可以通过该下载地址抓取文件；远程 Python 或手机测试请将 base URL 改成它们可以访问的 Java 地址，并设置前端跨域来源。

测试结束后设置 `A12_STORAGE_PROVIDER=oss` 并重启 Java，即恢复后续文件上传到 OSS。配置好原有 `aliyun.oss` 的 Bucket、Endpoint、密钥和 OSS CORS。

切换不会自动搬迁已有文件，也不会改数据库表。原 OSS 文件仍使用 OSS；本地文件用 `local/` 对象键标识，切回 OSS 后仍可下载，但必须保留本地目录及 Java 地址。数据库文件地址不含授权签名，请使用资源的 `download-url` 接口获取临时下载地址。不要将本地文件目录提交到 Git。
